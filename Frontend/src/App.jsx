import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthGuard }            from '@/guards/AuthGuard'
import { RoleGuard }            from '@/guards/RoleGuard'
import { LoginPage }            from '@/pages/LoginPage'
import { RegisterPage }         from '@/pages/RegisterPage'
import { ResetPasswordPage }    from '@/pages/ResetPasswordPage'
import { FeedPage }             from '@/pages/FeedPage'
import { ThreadDetailPage }     from '@/pages/ThreadDetailPage'
import { CreateThreadPage }     from '@/pages/CreateThreadPage'
import { NotificationsPage }    from '@/pages/NotificationsPage'
import { SearchPage }           from '@/pages/SearchPage'
import { ProfilePage }          from '@/pages/ProfilePage'
import { AdminDashboard }       from '@/pages/AdminDashboard'
import { ModDashboard }         from '@/pages/ModDashboard'

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path='/login'           element={<LoginPage />} />
          <Route path='/register'        element={<RegisterPage />} />
          <Route path='/reset-password'  element={<ResetPasswordPage />} />

          {/* Auth required */}
          <Route element={<AuthGuard />}>
            <Route path='/'        element={<Navigate to='/feed' replace />} />
            <Route path='/feed'    element={<FeedPage />} />
            <Route path='/threads/:id' element={<ThreadDetailPage />} />
            <Route path='/threads/new' element={<CreateThreadPage />} />
            <Route path='/notifications' element={<NotificationsPage />} />
            <Route path='/search'  element={<SearchPage />} />
            <Route path='/profile/:username' element={<ProfilePage />} />

            {/* Moderator+ */}
            <Route element={<RoleGuard minRole='moderator' />}>
              <Route path='/mod' element={<ModDashboard />} />
            </Route>

            {/* Admin only */}
            <Route element={<RoleGuard minRole='admin' />}>
              <Route path='/admin' element={<AdminDashboard />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
