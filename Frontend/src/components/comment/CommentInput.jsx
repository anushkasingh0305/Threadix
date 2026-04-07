import { useState, useRef } from 'react'
import { mentionsApi } from '@/api/mentions'

export function CommentInput({ onSubmit, placeholder = 'Write a comment...', autoFocus }) {
  const [content, setContent]   = useState('')
  const [mentions, setMentions] = useState([])
  const [loading, setLoading]   = useState(false)
  const debounceRef = useRef()

  const handleChange = (e) => {
    const val = e.target.value
    setContent(val)

    const match = val.slice(0, e.target.selectionStart).match(/@(\w*)$/)
    if (match) {
      const prefix = match[1]
      clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(async () => {
        if (prefix.length === 0) { setMentions([]); return }
        const res = await mentionsApi.search(prefix)
        setMentions(res.data)
      }, 200)
    } else {
      setMentions([])
    }
  }

  const insertMention = (username) => {
    setContent(prev => prev.replace(/@\w*$/, `@${username} `))
    setMentions([])
  }

  const handleSubmit = async () => {
    if (!content.trim()) return
    setLoading(true)
    await onSubmit(content)
    setContent('')
    setLoading(false)
  }

  return (
    <div className='relative'>
      <textarea
        value={content} onChange={handleChange}
        autoFocus={autoFocus}
        placeholder={placeholder}
        rows={3}
        className='w-full p-3 text-sm border border-gray-200 rounded-lg resize-none
                   focus:outline-none focus:ring-2 focus:ring-brand-light'
      />

      {/* @mention dropdown */}
      {mentions.length > 0 && (
        <div className='absolute z-10 left-0 w-64 bg-white border border-gray-200 rounded-lg
                        shadow-sm mt-1 overflow-hidden'>
          {mentions.map(u => (
            <button key={u.id} onMouseDown={() => insertMention(u.username)}
              className='w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50'>
              <div className='w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center
                              text-xs font-medium text-blue-700'>
                {u.username.slice(0, 2).toUpperCase()}
              </div>
              {u.username}
            </button>
          ))}
          <p className='px-3 py-1.5 text-xs text-gray-400 border-t'>
            {mentions.length} match{mentions.length !== 1 ? 'es' : ''}
          </p>
        </div>
      )}

      <div className='flex justify-end mt-2'>
        <button onClick={handleSubmit} disabled={loading || !content.trim()}
          className='px-4 py-1.5 text-sm bg-brand text-white rounded-lg disabled:opacity-50
                     hover:bg-brand-light transition'>
          {loading ? 'Posting...' : 'Post'}
        </button>
      </div>
    </div>
  )
}
