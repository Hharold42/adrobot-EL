const BASE = '/api'

function authHeaders() {
  const key = localStorage.getItem('keitaro_api_key')
  return key ? { 'X-Keitaro-Key': key } : {}
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail ?? detail
    } catch {
      /* тело не JSON — оставляем statusText */
    }
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    throw new Error(message)
  }
  return res.json()
}

export const api = {
  keitaroStatus: () => request('/keitaro/status'),
  offers: (search = '') => request(`/offers?search=${encodeURIComponent(search)}`),
  countries: () => request('/offers/countries'),
  campaigns: () => request('/campaigns'),
  campaign: (id) => request(`/campaigns/${id}`),
  keitaroCampaigns: () => request('/campaigns/keitaro'),
  importCampaigns: (keitaroIds) =>
    request('/campaigns/import', {
      method: 'POST',
      body: JSON.stringify({ keitaro_ids: keitaroIds }),
    }),
  createCampaign: (payload) =>
    request('/campaigns', { method: 'POST', body: JSON.stringify(payload) }),
  fetchStreams: (campaignId) =>
    request(`/campaigns/${campaignId}/fetch`, { method: 'POST' }),
  addOffer: (streamId, offerId) =>
    request(`/streams/${streamId}/offers`, {
      method: 'POST',
      body: JSON.stringify({ offer_id: offerId }),
    }),
  removeOffer: (streamId, offerId) =>
    request(`/streams/${streamId}/offers/${offerId}`, { method: 'DELETE' }),
  restoreOffer: (streamId, offerId) =>
    request(`/streams/${streamId}/offers/${offerId}/restore`, { method: 'POST' }),
  patchOffer: (streamId, offerId, patch) =>
    request(`/streams/${streamId}/offers/${offerId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  pushStream: (streamId) => request(`/streams/${streamId}/push`, { method: 'POST' }),
  cancelStream: (streamId) => request(`/streams/${streamId}/cancel`, { method: 'POST' }),
}
