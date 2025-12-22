export function readSessionJSON(key, fallback = null) {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch (error) {
    return fallback
  }
}

export function writeSessionJSON(key, value) {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    // ignore quota / private mode errors
  }
}

export function isValidYmdDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
}

export function isValidDateRange(value) {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    isValidYmdDate(value[0]) &&
    isValidYmdDate(value[1])
  )
}


