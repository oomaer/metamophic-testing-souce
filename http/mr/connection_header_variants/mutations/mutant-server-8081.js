const http = require('http');

const port = 8081;

// ============================================================================
// MUTATION TESTING SERVER
// Set MUTATION environment variable to activate a specific mutation
// Usage: MUTATION=M1 node mutant-server-3001.js
// ============================================================================

const MUTATION = process.env.MUTATION || 'NONE';

console.log(`[Mutant Server] Starting with mutation: ${MUTATION}`);

// Helper to send JSON response with Content-Length (not chunked)
function sendJson(res, statusCode, data) {
  const body = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body)
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  console.log(`[Port ${port}] ${req.method} ${req.url} [Mutation: ${MUTATION}]`);

  const connectionHeader = req.headers['connection'] || '';
  const isCloseConnection = connectionHeader.toLowerCase() === 'close';

  // ============================================================================
  // ROOT ENDPOINT: /
  // ============================================================================
  if (req.url === '/' && req.method === 'GET') {

    // M1: Different status for close - Return 201 instead of 200
    if (MUTATION === 'M1' && isCloseConnection) {
      sendJson(res, 201, { message: 'Success', status: 200 });
      return;
    }

    // M2: Error on close - Return 500
    if (MUTATION === 'M2' && isCloseConnection) {
      sendJson(res, 500, { message: 'Success', status: 200 });
      return;
    }

    // M3: Return 204 No Content
    if (MUTATION === 'M3' && isCloseConnection) {
      res.writeHead(204, { 'Content-Length': '0' });
      res.end();
      return;
    }

    // M8: Empty body
    if (MUTATION === 'M8' && isCloseConnection) {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Content-Length': '0' });
      res.end();
      return;
    }

    // M20: Different transfer encoding (chunked vs content-length)
    // This should NOT be detected - body content is the same
    if (MUTATION === 'M20' && isCloseConnection) {
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Transfer-Encoding': 'chunked'
      });
      const body = JSON.stringify({ message: 'Success', status: 200 });
      res.write(body);
      res.end();
      return;
    }

    // Default: Normal response with Content-Length
    sendJson(res, 200, { message: 'Success', status: 200 });
  }

  // ============================================================================
  // DATA ENDPOINT: /data
  // ============================================================================
  else if (req.url === '/data' && req.method === 'GET') {

    // M1: Different status for close
    if (MUTATION === 'M1' && isCloseConnection) {
      sendJson(res, 201, { data: 'test data', status: 200 });
      return;
    }

    // M2: Error on close
    if (MUTATION === 'M2' && isCloseConnection) {
      sendJson(res, 500, { data: 'test data', status: 200 });
      return;
    }

    // M3: Return 204 No Content
    if (MUTATION === 'M3' && isCloseConnection) {
      res.writeHead(204, { 'Content-Length': '0' });
      res.end();
      return;
    }

    // M8: Empty body
    if (MUTATION === 'M8' && isCloseConnection) {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Content-Length': '0' });
      res.end();
      return;
    }

    // M20: Different transfer encoding
    if (MUTATION === 'M20' && isCloseConnection) {
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Transfer-Encoding': 'chunked'
      });
      const body = JSON.stringify({ data: 'test data', status: 200 });
      res.write(body);
      res.end();
      return;
    }

    // Default: Normal response with Content-Length
    sendJson(res, 200, { data: 'test data', status: 200 });
  }

  // ============================================================================
  // OTHER ENDPOINTS
  // ============================================================================
  else {
    res.writeHead(404, { 'Content-Type': 'text/plain', 'Content-Length': '13' });
    res.end('404 Not Found');
  }
});

server.listen(port, () => {
  console.log(`[Mutant Server B] Listening on port ${port} with mutation: ${MUTATION}`);
});
