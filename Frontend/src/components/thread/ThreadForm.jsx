import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { tagsApi }    from '@/api/tags'
import { cn } from '@/lib/utils'

export function ThreadForm({ threadId, initialTitle = '', initialDesc = '', initialTagIds = [], onSuccess }) {
  const navigate = useNavigate()
  const [title, setTitle]       = useState(initialTitle)
  const [desc, setDesc]         = useState(initialDesc)
  const [selectedTags, setTags] = useState(initialTagIds)
  const [files, setFiles]       = useState([])
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const { data: tags } = useQuery({
    queryKey: ['tags'],
    queryFn: () => tagsApi.getAll().then(r => r.data),
  })

  const toggleTag = (id) =>
    setTags(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id].slice(0, 5))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || !desc.trim()) { setError('Title and description are required'); return }
    setLoading(true)
    try {
      if (threadId) {
        await threadsApi.update(threadId, { title, description: desc, tag_ids: selectedTags })
        onSuccess?.(threadId)
      } else {
        const fd = new FormData()
        fd.append('title', title)
        fd.append('description', desc)
        if (selectedTags.length) fd.append('tag_ids', selectedTags.join(','))
        files.forEach(f => fd.append('files', f))
        const res = await threadsApi.create(fd)
        onSuccess ? onSuccess(res.data.id) : navigate(`/threads/${res.data.id}`)
      }
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Failed to save thread')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className='space-y-5'>
      <div>
        <label className='text-sm font-medium text-gray-700'>Title</label>
        <input value={title} onChange={e => setTitle(e.target.value)} maxLength={200}
          className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none
                     focus:ring-2 focus:ring-brand-light'
          placeholder='Give your thread a clear title...' />
      </div>
      <div>
        <label className='text-sm font-medium text-gray-700'>Description</label>
        <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={5}
          className='mt-1 w-full px-3 py-2 text-sm border rounded-lg resize-none
                     focus:outline-none focus:ring-2 focus:ring-brand-light'
          placeholder='What do you want to discuss?' />
      </div>
      {!threadId && (
        <div>
          <label className='text-sm font-medium text-gray-700'>
            Media <span className='text-gray-400 font-normal'>(optional, up to 5 files)</span>
          </label>
          <div className='mt-1 border-2 border-dashed border-gray-200 rounded-lg p-6 text-center'>
            <input type='file' multiple accept='image/*,video/*'
              onChange={e => setFiles(Array.from(e.target.files ?? []).slice(0, 5))}
              className='hidden' id='media-upload' />
            <label htmlFor='media-upload' className='cursor-pointer text-sm text-gray-500'>
              {files.length > 0
                ? `${files.length} file${files.length > 1 ? 's' : ''} selected`
                : 'Click to upload images or videos'}
            </label>
          </div>
        </div>
      )}
      <div>
        <label className='text-sm font-medium text-gray-700'>
          Tags <span className='text-gray-400 font-normal'>(up to 5)</span>
        </label>
        <div className='mt-2 flex flex-wrap gap-2'>
          {(tags ?? []).map((t) => (
            <button key={t.id} type='button' onClick={() => toggleTag(t.id)}
              className={cn('px-3 py-1 text-xs rounded-full border transition',
                selectedTags.includes(t.id)
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-gray-300'
              )}>
              {t.name}
            </button>
          ))}
        </div>
      </div>
      {error && <p className='text-sm text-red-500'>{error}</p>}
      <div className='flex justify-end gap-3'>
        <button type='button' onClick={() => navigate(-1)}
          className='px-4 py-2 text-sm border rounded-lg hover:bg-gray-50'>Cancel
        </button>
        <button type='submit' disabled={loading}
          className='px-4 py-2 text-sm bg-brand text-white rounded-lg
                     hover:bg-brand-light disabled:opacity-50 transition'>
          {loading ? 'Saving...' : threadId ? 'Save changes' : 'Publish thread'}
        </button>
      </div>
    </form>
  )
}
