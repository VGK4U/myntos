/**
 * PRODUCTION CODE LIFECYCLE TESTS
 * Directly imports and tests the actual production functions from server.js!
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// IMPORT DIRECTLY FROM PRODUCTION SERVER.JS
const {
    processConnectionUpdate,
    getConnectionStatus,
    setConnectionStatus,
    getClientGen,
    setClientGen,
    getSkipRestoreOnce,
    setSkipRestoreOnce,
    AUTH_DIR
} = require('./server');

console.log('--- STARTING DIRECT PRODUCTION LIFECYCLE TESTS (server.js) ---');

// Ensure dummy creds.json exists in AUTH_DIR for test validation
if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });
const dummyCredsPath = path.join(AUTH_DIR, 'creds.json');
fs.writeFileSync(dummyCredsPath, JSON.stringify({ me: { id: '919876543210:1@s.whatsapp.net' } }));

async function runProductionTests() {
    // Set baseline generation and status
    setClientGen(10);
    setConnectionStatus('connected');
    setSkipRestoreOnce(false);

    // 1. Temporary Disconnect (Generic Error) -> MUST PRESERVE CREDENTIALS
    console.log('1. Testing Production processConnectionUpdate on generic temporary socket close:');
    fs.writeFileSync(dummyCredsPath, JSON.stringify({ valid: true }));
    let res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: new Error('Generic socket close') }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'reconnecting', 'Production status must transition to reconnecting');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Production code must NOT delete creds.json on temporary disconnect');
    console.log('   PASS: Generic socket disconnect preserved credentials and transitioned to reconnecting.');

    // 2. HTTP 408 (Timed Out) -> MUST PRESERVE CREDENTIALS
    console.log('2. Testing Production processConnectionUpdate on 408 (timedOut):');
    res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 408 }, message: 'Timed out' } }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'reconnecting');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Production code must NOT delete creds.json on 408');
    console.log('   PASS: 408 preserved credentials.');

    // 3. HTTP 428 (Connection Closed) -> MUST PRESERVE CREDENTIALS
    console.log('3. Testing Production processConnectionUpdate on 428 (connectionClosed):');
    res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 428 }, message: 'Connection closed' } }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'reconnecting');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Production code must NOT delete creds.json on 428');
    console.log('   PASS: 428 preserved credentials.');

    // 4. HTTP 515 (Restart Required) -> MUST PRESERVE CREDENTIALS
    console.log('4. Testing Production processConnectionUpdate on 515 (restartRequired):');
    res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 515 }, message: 'Restart required' } }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'reconnecting');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Production code must NOT delete creds.json on 515');
    console.log('   PASS: 515 preserved credentials.');

    // 5. ECONNRESET -> MUST PRESERVE CREDENTIALS
    console.log('5. Testing Production processConnectionUpdate on ECONNRESET:');
    res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: { code: 'ECONNRESET', message: 'read ECONNRESET' } }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'reconnecting');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Production code must NOT delete creds.json on ECONNRESET');
    console.log('   PASS: ECONNRESET preserved credentials.');

    // 6. STALE CLIENT GENERATION (Gen 9) receives 401 when Gen 10 is active -> MUST BE DROPPED
    console.log('6. Testing Stale Generation Guard in Production code (Gen 9 event on Gen 10 active):');
    setConnectionStatus('connected');
    res = await processConnectionUpdate(9, {
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 401 } } }
    });
    assert.strictEqual(res.dropped, true, 'Stale generation event must be dropped');
    assert.strictEqual(getConnectionStatus(), 'connected', 'Stale event must NOT alter active connection state');
    assert.strictEqual(fs.existsSync(dummyCredsPath), true, 'Stale event must NOT delete credentials');
    console.log('   PASS: Stale generation 401 was safely dropped without modifying active session.');

    // 7. CURRENT CLIENT GENERATION (Gen 10) receives genuine 401 -> MUST INVALIDATE SESSION
    console.log('7. Testing Terminal 401 on CURRENT Generation (Gen 10):');
    res = await processConnectionUpdate(10, {
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 401 } } }
    });
    assert.strictEqual(res.dropped, false);
    assert.strictEqual(getConnectionStatus(), 'qr_ready', 'Must transition to qr_ready on real 401');
    assert.strictEqual(fs.existsSync(dummyCredsPath), false, 'Must purge local creds on genuine 401');
    assert.strictEqual(getSkipRestoreOnce(), true, 'skipRestoreOnce must be true to prevent S3 restore loop');
    console.log('   PASS: Terminal 401 on current generation cleanly invalidated dead session.');

    // Advance generation to disarm setTimeout from test 7
    setClientGen(999);

    console.log('ALL PRODUCTION LIFECYCLE TESTS IN SERVER.JS VERIFIED AND PASSED!');
    process.exit(0);
}

runProductionTests().catch(err => {
    console.error('Production test failure:', err);
    process.exit(1);
});
