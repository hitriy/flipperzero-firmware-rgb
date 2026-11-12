export async function downloadFirmware(url: string) {
  // Pages assets must resolve against this site, not the catalog API baseURL.
  const response = await fetch(new URL(url, location.origin))
  if (!response.ok) throw new Error(`Firmware download failed (HTTP ${response.status})`)
  return response.arrayBuffer()
}
