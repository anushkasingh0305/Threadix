import { useEffect, useRef, useCallback } from 'react'
import { WS_BASE } from '@/lib/constants'

export function useWebSocket({ channels, onMessage, enabled = true }) {
  const wsRef    = useRef(null)
  const retryRef = useRef()
  const delay    = useRef(1000)
  const channelsKey = channels.join(',')

  const connect = useCallback(() => {
    if (!enabled || channels.length === 0) return
    const url = `${WS_BASE}/ws?channels=${channelsKey}`
    const ws  = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) }
      catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      retryRef.current = setTimeout(() => {
        delay.current = Math.min(delay.current * 2, 30_000)
        connect()
      }, delay.current)
    }

    ws.onopen = () => { delay.current = 1000 }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelsKey, enabled])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])
}
