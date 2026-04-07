import { Heart } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { cn } from '@/lib/utils'

export function LikeButton({ threadId, liked, likeCount }) {
  const qc = useQueryClient()
  const mut = useMutation({
    mutationFn: () => threadsApi.toggleLike(threadId),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['thread', threadId] }),
  })

  return (
    <button onClick={() => mut.mutate()}
      className={cn('flex items-center gap-1 text-sm transition',
        liked ? 'text-red-500' : 'text-gray-400 hover:text-red-400')}>
      <Heart className='w-4 h-4' fill={liked ? 'currentColor' : 'none'} />
      {likeCount}
    </button>
  )
}
