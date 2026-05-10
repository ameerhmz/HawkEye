/**
 * Convert an HTTP(S) LiveKit URL to the WebSocket equivalent.
 * LiveKit client SDK expects ws:// or wss:// URLs.
 */
export function normalizeLiveKitUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http://")) return url.replace("http://", "ws://");
  if (url.startsWith("https://")) return url.replace("https://", "wss://");
  return url;
}
