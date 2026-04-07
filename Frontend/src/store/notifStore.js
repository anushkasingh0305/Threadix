import { create } from 'zustand'

export const useNotifStore = create((set) => ({
  unreadCount: 0,
  setCount:  (n) => set({ unreadCount: n }),
  increment: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  reset:     () => set({ unreadCount: 0 }),
}))
