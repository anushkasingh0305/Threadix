import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

const schema = z.object({
  email:    z.string().email(),
  password: z.string().min(6),
})

export function LoginPage() {
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })
  const setUser = useAuthStore((s) => s.setUser)
  const navigate = useNavigate()
  const [error, setError] = useState('')

  const onSubmit = async (data) => {
    try {
      await authApi.login(data)
      const profile = await authApi.getProfile()
      setUser(profile.data)
      navigate('/feed')
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Login failed')
    }
  }

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50'>
      <div className='w-full max-w-sm card'>
        <h1 className='text-2xl font-semibold text-brand mb-6'>Log in to Threadix</h1>
        <form onSubmit={handleSubmit(onSubmit)} className='space-y-4'>
          <div>
            <label className='text-sm font-medium text-gray-700'>Email</label>
            <input {...register('email')} type='email'
              className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                         focus:ring-2 focus:ring-brand-light' />
            {errors.email && <p className='text-xs text-red-500 mt-1'>{errors.email.message}</p>}
          </div>
          <div>
            <label className='text-sm font-medium text-gray-700'>Password</label>
            <input {...register('password')} type='password'
              className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                         focus:ring-2 focus:ring-brand-light' />
            {errors.password && <p className='text-xs text-red-500 mt-1'>{errors.password.message}</p>}
          </div>
          {error && <p className='text-sm text-red-500'>{error}</p>}
          <button type='submit'
            className='w-full py-2 bg-brand text-white rounded-lg text-sm hover:bg-brand-light transition'>
            Log in
          </button>
        </form>
        <div className='mt-4 text-center text-sm text-gray-500'>
          <span>No account? <Link to='/register' className='text-brand hover:underline'>Register</Link></span>
        </div>
      </div>
    </div>
  )
}
