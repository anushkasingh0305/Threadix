import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { authApi } from '@/api/auth'

const schema = z.object({
  username: z.string().min(3).max(20),
  email:    z.string().email(),
  password: z.string().min(6),
})

const fields = [
  { name: 'username', label: 'Username', type: 'text' },
  { name: 'email',    label: 'Email',    type: 'email' },
  { name: 'password', label: 'Password', type: 'password' },
]

export function RegisterPage() {
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })
  const navigate = useNavigate()
  const [error, setError] = useState('')

  const onSubmit = async (data) => {
    try {
      await authApi.register(data)
      navigate('/login')
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Registration failed')
    }
  }

  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-50'>
      <div className='w-full max-w-sm card'>
        <h1 className='text-2xl font-semibold text-brand mb-6'>Create an account</h1>
        <form onSubmit={handleSubmit(onSubmit)} className='space-y-4'>
          {fields.map(f => (
            <div key={f.name}>
              <label className='text-sm font-medium text-gray-700'>{f.label}</label>
              <input {...register(f.name)} type={f.type}
                className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                           focus:ring-2 focus:ring-brand-light' />
              {errors[f.name] && (
                <p className='text-xs text-red-500 mt-1'>{errors[f.name]?.message}</p>
              )}
            </div>
          ))}
          {error && <p className='text-sm text-red-500'>{error}</p>}
          <button type='submit'
            className='w-full py-2 bg-brand text-white rounded-lg text-sm hover:bg-brand-light transition'>
            Create account
          </button>
        </form>
        <p className='mt-4 text-center text-sm text-gray-500'>
          Already have an account? <Link to='/login' className='text-brand hover:underline'>Log in</Link>
        </p>
      </div>
    </div>
  )
}
