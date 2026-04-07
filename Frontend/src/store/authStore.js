import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(persist(
  (set) => ({
    user:     null,
    isAuthed: false,
    setUser:  (u) => set({ user: u, isAuthed: true }),
    logout:   () => set({ user: null, isAuthed: false }),
  }),
  { name: 'threadix-auth' }
))
