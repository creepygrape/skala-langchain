export async function createTicketGuide({ url, question }) {
  const response = await fetch('/api/guide', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, question }),
  })

  if (!response.ok) {
    let message = '예매 정보를 확인하지 못했습니다. 잠시 후 다시 시도해주세요.'
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') message = payload.detail
    } catch {
      // Keep the fallback when the server does not return JSON.
    }
    throw new Error(message)
  }

  return response.json()
}
