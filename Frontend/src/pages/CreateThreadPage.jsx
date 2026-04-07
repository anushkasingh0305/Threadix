import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { tagsApi }    from '@/api/tags'
import { PageLayout } from '@/components/layout/PageLayout'
import { cn } from '@/lib/utils'

export function CreateThreadPage() {
  const navigate     = useNavigate()
  const queryClient  = useQueryClient()
  const [title, setTitle]         = useState('')
  const [desc, setDesc]           = useState('')
  const [selectedTags, setTags]   = useState([])
  const [files, setFiles]         = useState([])
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [newTag, setNewTag]       = useState('')
  const [tagError, setTagError]   = useState('')
  const [tagLoading, setTagLoading] = useState(false)

  const { data: tags } = useQuery({
    queryKey: ['tags'],
    queryFn: () => tagsApi.getAll().then(r => r.data),
  })

  const toggleTag = (id) =>
    setTags(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id].slice(0, 5))

  const handleCreateTag = async () => {
    const name = newTag.trim()
    if (!name) return
    setTagError('')
    setTagLoading(true)
    try {
      const res = await tagsApi.create(name)
      const created = res.data
      await queryClient.invalidateQueries({ queryKey: ['tags'] })
      setTags(prev => [...prev, created.id].slice(0, 5))
      setNewTag('')
    } catch (e) {
      setTagError(e?.response?.data?.detail ?? 'Could not create tag')
    } finally {
      setTagLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || !desc.trim()) { setError('Title and description are required'); return }
    setLoading(true)
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', desc)
    if (selectedTags.length) fd.append('tag_ids', selectedTags.join(','))
    files.forEach(f => fd.append('files', f))
    try {
      const res = await threadsApi.create(fd)
      navigate(`/threads/${res.data.id}`)
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Failed to create thread')
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageLayout>
      <div className='max-w-2xl'>
        <h1 className='text-xl font-semibold mb-6'>Create a new thread</h1>
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
              placeholder='What do you want to discuss? Use @username to mention someone.' />
          </div>
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
            <div className='mt-3 flex gap-2'>
              <input
                type='text'
                value={newTag}
                onChange={e => setNewTag(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleCreateTag())}
                maxLength={30}
                placeholder='Create a new tag...'
                className='flex-1 px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-light'
              />
              <button
                type='button'
                onClick={handleCreateTag}
                disabled={tagLoading || !newTag.trim()}
                className='px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition'>
                {tagLoading ? '...' : '+ Add'}
              </button>
            </div>
            {tagError && <p className='mt-1 text-xs text-red-500'>{tagError}</p>}
          </div>
          {error && <p className='text-sm text-red-500'>{error}</p>}
          <div className='flex justify-end gap-3'>
            <button type='button' onClick={() => navigate(-1)}
              className='px-4 py-2 text-sm border rounded-lg hover:bg-gray-50'>Cancel
            </button>
            <button type='submit' disabled={loading}
              className='px-4 py-2 text-sm bg-brand text-white rounded-lg
                         hover:bg-brand-light disabled:opacity-50 transition'>
              {loading ? 'Publishing...' : 'Publish thread'}
            </button>
          </div>
        </form>
      </div>
    </PageLayout>
  )
}
