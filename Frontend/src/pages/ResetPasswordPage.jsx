import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { authApi } from '@/api/auth'

export function ResetPasswordPage() {
  const [params]     = useSearchParams()
  const token        = params.get('token') ?? ''
  const navigate     = useNavigate()
  const [password,   setPassword]   = useState('')
  const [confirm,    setConfirm]    = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password.length < 6)      { setError('Password must be at least 6 characters'); return }
    if (password !== confirm)     { setError('Passwords do not match'); return }
    if (!token)                   { setError('Invalid or missing reset token'); return }
    setLoading(true)
    setError('')
    try {
      await authApi.resetPassword(token, password)
      navigate('/login', { state: { message: 'Password reset successfully. Please log in.' } })
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Reset failed. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50'>
      <div className='w-full max-w-sm card'>
        <h1 className='text-2xl font-semibold text-brand mb-2'>Reset password</h1>
        <p className='text-sm text-gray-500 mb-6'>Enter your new password below.</p>
        <form onSubmit={handleSubmit} className='space-y-4'>
          <div>
            <label className='text-sm font-medium text-gray-700'>New password</label>
            <input type='password' value={password} onChange={e => setPassword(e.target.value)}
              minLength={6} required
              className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                         focus:ring-2 focus:ring-brand-light' />
          </div>
          <div>
            <label className='text-sm font-medium text-gray-700'>Confirm password</label>
            <input type='password' value={confirm} onChange={e => setConfirm(e.target.value)}
              required
              className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                         focus:ring-2 focus:ring-brand-light' />
          </div>
          {error && <p className='text-sm text-red-500'>{error}</p>}
          <button type='submit' disabled={loading}
            className='w-full py-2 bg-brand text-white rounded-lg text-sm hover:bg-brand-light
                       disabled:opacity-50 transition'>
            {loading ? 'Resetting...' : 'Reset password'}
          </button>
        </form>
        <p className='mt-4 text-center text-sm'>
          <Link to='/login' className='text-brand hover:underline'>Back to login</Link>
        </p>
      </div>
    </div>
  )
}
