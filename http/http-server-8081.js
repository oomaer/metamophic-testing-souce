const http = require('http');

const port = 8081;

// Large static content for range request testing (same as server 3000)
const LARGE_CONTENT = `Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris. Integer in mauris eu nibh euismod gravida. Duis ac tellus et risus vulputate vehicula. Donec lobortis risus a elit. Etiam tempor. Ut ullamcorper, ligula eu tempor congue, eros est euismod turpis, id tincidunt sapien risus a quam. Maecenas fermentum consequat mi. Donec fermentum. Pellentesque malesuada nulla a mi. Duis sapien sem, aliquet sed, vulputate eget, feugiat non, arcu.`;

function parseRangeHeader(rangeHeader, totalSize) {
  if (!rangeHeader || !rangeHeader.startsWith('bytes=')) {
    return null;
  }

  const rangeSpec = rangeHeader.slice(6); // Remove 'bytes='
  const ranges = [];

  for (const part of rangeSpec.split(',')) {
    const trimmed = part.trim();

    if (trimmed.startsWith('-')) {
      // Suffix range: -500 means last 500 bytes
      const suffixLength = parseInt(trimmed.slice(1), 10);
      if (isNaN(suffixLength)) return null;
      const start = Math.max(0, totalSize - suffixLength);
      ranges.push({ start, end: totalSize - 1 });
    } else if (trimmed.endsWith('-')) {
      // Open-ended range: 500- means from 500 to end
      const start = parseInt(trimmed.slice(0, -1), 10);
      if (isNaN(start)) return null;
      ranges.push({ start, end: totalSize - 1 });
    } else {
      // Normal range: 0-499
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

const server = http.createServer((req, res) => {
  console.log(`[Port ${port}] ${req.method} ${req.url}`);
  console.log('Headers:', req.headers);


  // Existing endpoints (unchanged for MR1 compatibility)
  if (req.url === '/' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json'});
    res.end(JSON.stringify({
      message: 'Success',
      status: 200
    }));
  } else if (req.url === '/data' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json'});
    res.end(JSON.stringify({
      data: 'test data',
      status: 200
    }));
  }
  // New endpoint for range request testing
  else if (req.url === '/large' && req.method === 'GET') {
    const content = Buffer.from(LARGE_CONTENT, 'utf-8');
    const totalSize = content.length;
    const rangeHeader = req.headers['range'];

    if (rangeHeader) {
      const ranges = parseRangeHeader(rangeHeader, totalSize);

      if (!ranges || ranges.length === 0) {
        // Invalid range
        res.writeHead(416, {
          'Content-Range': `bytes */${totalSize}`,
          'Content-Type': 'text/plain'
        });
        res.end('Range Not Satisfiable');
        return;
      }

      if (ranges[0].start >= totalSize) {
        // Range start beyond content
        res.writeHead(416, {
          'Content-Range': `bytes */${totalSize}`,
          'Content-Type': 'text/plain'
        });
        res.end('Range Not Satisfiable');
        return;
      }

      // Single range request (RFC 7233 Section 4.1)
      const range = ranges[0];
      const start = range.start;
      const end = Math.min(range.end, totalSize - 1);
      const chunkSize = end - start + 1;
      const chunk = content.slice(start, end + 1);

      res.writeHead(206, {
        'Content-Type': 'text/plain',
        'Content-Length': chunkSize,
        'Content-Range': `bytes ${start}-${end}/${totalSize}`,
        'Accept-Ranges': 'bytes'
      });
      res.end(chunk);
    } else {
      // Full content request
      res.writeHead(200, {
        'Content-Type': 'text/plain',
        'Content-Length': totalSize,
        'Accept-Ranges': 'bytes'
      });
      res.end(content);
    }
  }
  else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('404 Not Found');
  }
});

server.listen(port, () => {
  console.log(`Server B is listening on port ${port}`);
});
