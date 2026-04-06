import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 120000,
})

export const getTeams = () => api.get('/teams/').then(r => r.data)

export const getTeamTrios = (teamId, filters = []) => {
  const params = {}
  if (filters.length) params.filters = filters.join(',')
  return api.get(`/teams/${teamId}/trios/`, { params }).then(r => r.data)
}

export const getTrioDetail = (trioKey, teamId, filters = []) => {
  const params = {}
  if (teamId) params.team_id = teamId
  if (filters.length) params.filters = filters.join(',')
  return api.get(`/trios/${trioKey}/`, { params }).then(r => r.data)
}

export const getFreshness = () => api.get('/meta/freshness/').then(r => r.data)

export default api
