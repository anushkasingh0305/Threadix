import { CommentNode } from './CommentNode'

export function CommentTree({ comments, threadId }) {
  return (
    <div className='space-y-3'>
      {comments.map(c => (
        <CommentNode key={c.id} comment={c} threadId={threadId} />
      ))}
    </div>
  )
}
