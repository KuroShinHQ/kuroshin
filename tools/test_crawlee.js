try {
  const c = require('./node_modules/crawlee/index.js');
  console.log('Crawlee OK, keys:', Object.keys(c).slice(0, 5).join(', '));
} catch(e) {
  console.error('FAIL:', e.message);
}
process.exit(0);
