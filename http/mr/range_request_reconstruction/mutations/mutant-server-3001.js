const http = require('http');

const port = Number(process.env.PORT || 8081);

// ============================================================================
// MUTATION TESTING SERVER — Range Request Reconstruction MR
// Set MUTATION environment variable to activate a specific mutation.
// Usage: MUTATION=M1 node mutant-server-3001.js
//
// The MR under test:
//   A: GET /large (no Range)                → 200, full body
//   B: GET /large  Range: bytes=0-(k-1)     → 206, part1
//      GET /large  Range: bytes=k-          → 206, part2
//   Relation: body(part1) + body(part2) == body(full)
//
// Each mutation targets the range-serving path in some realistic way.
// ============================================================================

const MUTATION = process.env.MUTATION || 'NONE';

console.log(`[Mutant Server] Starting with mutation: ${MUTATION}`);

// Large static content — MUST match http-server-8080.js byte-for-byte.
const LARGE_CONTENT = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris. Integer in mauris eu nibh euismod gravida. Duis ac tellus et risus vulputate vehicula. Donec lobortis risus a elit. Etiam tempor. Ut ullamcorper, ligula eu tempor congue, eros est euismod turpis, id tincidunt sapien risus a quam. Maecenas fermentum consequat mi. Donec fermentum. Pellentesque malesuada nulla a mi. Duis sapien sem, aliquet sed, vulputate eget, feugiat non, arcu.`;

// ---------------------------------------------------------------------------
// Range parser (baseline is the same as http-server-8081.js).
// A couple of mutations swap in a broken variant.
// ---------------------------------------------------------------------------
function parseRangeHeader(rangeHeader, totalSize) {
  if (!rangeHeader || !rangeHeader.startsWith('bytes=')) {
    return null;
  }

  const rangeSpec = rangeHeader.slice(6);
  const ranges = [];

  for (const part of rangeSpec.split(',')) {
    const trimmed = part.trim();

    if (trimmed.startsWith('-')) {
      const suffixLength = parseInt(trimmed.slice(1), 10);
      if (isNaN(suffixLength)) return null;
      const start = Math.max(0, totalSize - suffixLength);
      ranges.push({ start, end: totalSize - 1 });
    } else if (trimmed.endsWith('-')) {
      const start = parseInt(trimmed.slice(0, -1), 10);
      if (isNaN(start)) return null;
      ranges.push({ start, end: totalSize - 1 });
    } else {
      const [startStr, endStr] = trimmed.split('-');
      const start = parseInt(startStr, 10);
      const end = parseInt(endStr, 10);
      if (isNaN(start) || isNaN(end)) return null;
      if (start > end) return null;
      ranges.push({ start, end: Math.min(end, totalSize - 1) });
    }
  }

  return ranges.length > 0 ? ranges : null;
}

// M2 variant: naive regex parser where empty `end` defaults to `start`, not EOF.
// Real bug: /(\d+)-(\d*)/ with `end = endStr ? +endStr : start`.
function parseRangeHeader_M2(rangeHeader, totalSize) {
  if (!rangeHeader || !rangeHeader.startsWith('bytes=')) return null;
  const m = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
  if (!m) return null;
  const start = parseInt(m[1], 10);
  const end = m[2] === '' ? start : parseInt(m[2], 10);   // <-- bug
  if (isNaN(start) || isNaN(end)) return null;
  return [{ start, end: Math.min(end, totalSize - 1) }];
}

// M6 "cache": key by URL only, ignoring the Range header. First response for a
// given URL is remembered and served to every subsequent request.
const NAIVE_CACHE = new Map();

// M10 buffer: leaked bytes from the previous response on the same socket.
// Keyed by connection id; keep-alive state that never gets cleared.
const CONNECTION_STALE_BUFFER = new Map();

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------
const server = http.createServer((req, res) => {
  console.log(`[Port ${port}] ${req.method} ${req.url} [Mutation: ${MUTATION}]`);

  // Existing endpoints preserved for compatibility with the other MRs that
  // share this server surface.
  if (req.url === '/' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: 'Success', status: 200 }));
    return;
  }
  if (req.url === '/data' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ data: 'test data', status: 200 }));
    return;
  }

  if (req.url === '/large' && req.method === 'GET') {
    const content = Buffer.from(LARGE_CONTENT, 'utf-8');
    const totalSize = content.length;

    // M4: case-sensitive header lookup — Node lowercases everything, so this
    // ALWAYS misses and falls through to the "full body" branch.
    let rangeHeader;
    if (MUTATION === 'M4') {
      rangeHeader = req.headers['Range'];   // <-- always undefined
    } else {
      rangeHeader = req.headers['range'];
    }

    if (rangeHeader) {
      // Pick parser per-mutation.
      const ranges = (MUTATION === 'M2')
        ? parseRangeHeader_M2(rangeHeader, totalSize)
        : parseRangeHeader(rangeHeader, totalSize);

      if (!ranges || ranges.length === 0) {
        res.writeHead(416, {
          'Content-Range': `bytes */${totalSize}`,
          'Content-Type': 'text/plain'
        });
        res.end('Range Not Satisfiable');
        return;
      }
      if (ranges[0].start >= totalSize) {
        res.writeHead(416, {
          'Content-Range': `bytes */${totalSize}`,
          'Content-Type': 'text/plain'
        });
        res.end('Range Not Satisfiable');
        return;
      }

      const range = ranges[0];
      let start = range.start;
      let end = Math.min(range.end, totalSize - 1);
      const isOpenEnded = /^bytes=\d+-\s*$/.test(rangeHeader);

      // ---- M1: inclusive/exclusive end confusion ---------------------------
      // Real bug: treating `end` as exclusive when RFC says inclusive.
      if (MUTATION === 'M1') {
        const chunk = content.slice(start, end);           // drops last byte
        const chunkSize = chunk.length;
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': chunkSize,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- M11: Content-Length reflects the FULL file, not the chunk --------
      // Real nginx-style misconfig. Body is the right slice but the header
      // lies — the client will keep reading beyond EOF or truncate.
      if (MUTATION === 'M11') {
        const chunk = content.slice(start, end + 1);
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': totalSize,                     // <-- lie
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- M5: open-ended off-by-one (returns [start, totalSize-2]) --------
      if (MUTATION === 'M5' && isOpenEnded) {
        end = totalSize - 2;                               // drops last byte
      }

      // ---- M6: cache keyed by URL only ------------------------------------
      // Second request for /large returns the cached first response.
      if (MUTATION === 'M6') {
        if (NAIVE_CACHE.has(req.url)) {
          const cached = NAIVE_CACHE.get(req.url);
          res.writeHead(206, {
            'Content-Type': 'text/plain',
            'Content-Length': cached.chunk.length,
            'Content-Range': cached.contentRange,
            'Accept-Ranges': 'bytes'
          });
          res.end(cached.chunk);
          return;
        }
        const chunk = content.slice(start, end + 1);
        NAIVE_CACHE.set(req.url, {
          chunk,
          contentRange: `bytes ${start}-${end}/${totalSize}`
        });
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': chunk.length,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- M7: buffer overrun — always appends 2 stray bytes -------------
      // Real bug shape: server response buffer is sized `chunk.length + slack`
      // and the tail `slack` bytes get sent along with the payload. Reports
      // the true (padded) Content-Length so the mismatch is only visible in
      // the concatenated body — clean single-oracle detection.
      if (MUTATION === 'M7') {
        const chunk = content.slice(start, end + 1);
        const padded = Buffer.concat([chunk, Buffer.from('\x00\x00')]);
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': padded.length,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(padded);
        return;
      }

      // ---- M8: Content-Range lies, body is correct -------------------------
      if (MUTATION === 'M8') {
        const chunk = content.slice(start, end + 1);
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': chunk.length,
          'Content-Range': `bytes 0-99/${totalSize}`,      // <-- lie
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- M9: 200 OK with the correct partial slice -----------------------
      // Some servers fall back to 200 when they don't understand Range.
      if (MUTATION === 'M9') {
        const chunk = content.slice(start, end + 1);
        res.writeHead(200, {
          'Content-Type': 'text/plain',
          'Content-Length': chunk.length,
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- M10: keep-alive state leak; append stale bytes from prior req ---
      if (MUTATION === 'M10') {
        const connId = req.socket.remotePort + ':' + req.socket.remoteAddress;
        const stale = CONNECTION_STALE_BUFFER.get(connId) || Buffer.alloc(0);
        const chunk = content.slice(start, end + 1);
        const bleed = stale.slice(0, Math.min(8, stale.length));
        const outBody = Buffer.concat([bleed, chunk]);
        CONNECTION_STALE_BUFFER.set(connId, chunk);       // never cleared
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': outBody.length,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(outBody);
        return;
      }

      // ---- M3: silently drop the request past a fixed threshold -----------
      // Embedded HTTP stacks with fixed-size buffers do this.
      if (MUTATION === 'M3' && start > 512) {
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': 0,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(Buffer.alloc(0));
        return;
      }

      // ---- M12: UTF-8 "safe boundary" — never split mid-multibyte ----------
      // Rounds `end` down to the previous whitespace/ASCII boundary. For the
      // pure-ASCII payload here, we simulate the same rounding by snapping
      // `end` down to the nearest 8-byte boundary — same shape of bug,
      // deterministic and visible.
      if (MUTATION === 'M12' && end > start + 8) {
        const snapped = start + Math.floor((end - start + 1) / 8) * 8 - 1;
        if (snapped >= start) end = snapped;
        const chunk = content.slice(start, end + 1);
        res.writeHead(206, {
          'Content-Type': 'text/plain',
          'Content-Length': chunk.length,
          'Content-Range': `bytes ${start}-${end}/${totalSize}`,
          'Accept-Ranges': 'bytes'
        });
        res.end(chunk);
        return;
      }

      // ---- Baseline path (also used by M2 and M5 after they adjusted end) --
      const chunkSize = end - start + 1;
      const chunk = content.slice(start, end + 1);
      res.writeHead(206, {
        'Content-Type': 'text/plain',
        'Content-Length': chunkSize,
        'Content-Range': `bytes ${start}-${end}/${totalSize}`,
        'Accept-Ranges': 'bytes'
      });
      res.end(chunk);
      return;
    }

    // No Range header (or M4's case-sensitive lookup missed it) → full body.
    res.writeHead(200, {
      'Content-Type': 'text/plain',
      'Content-Length': totalSize,
      'Accept-Ranges': 'bytes'
    });
    res.end(content);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('404 Not Found');
});

server.listen(port, () => {
  console.log(`[Mutant Server B] Listening on port ${port} with mutation: ${MUTATION}`);
});
