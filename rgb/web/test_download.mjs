import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { after, before, test } from 'node:test'
import { downloadFirmware } from './firmwareDownload.ts'

const bytes = Buffer.from([0x1f, 0x8b, 0x08, 0x00])
const server = createServer((request, response) => {
  if (request.url === '/flipperzero-firmware-rgb/firmware/selected.tgz') {
    response.end(bytes)
  } else {
    response.writeHead(404).end('Not found')
  }
})
before(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  globalThis.location = { origin: `http://127.0.0.1:${server.address().port}` }
})
after(() => { server.close(); delete globalThis.location })

test('firmware paths resolve to the Pages origin and return binary bytes', async () => {
  const result = await downloadFirmware('/flipperzero-firmware-rgb/firmware/selected.tgz')
  assert.deepEqual(Buffer.from(result), bytes)
})
test('HTTP errors preserve the download failure instead of accessing undefined response.data', async () => {
  await assert.rejects(downloadFirmware('/missing.tgz'), /Firmware download failed \(HTTP 404\)/)
})
