import { Navbar }  from './Navbar'
import { Sidebar } from './Sidebar'

export function PageLayout({ children }) {
  return (
    <div className='min-h-screen bg-gray-50'>
      <Navbar />
      <div className='flex max-w-7xl mx-auto px-4 pt-4 gap-6'>
        <Sidebar />
        <main className='flex-1 min-w-0'>{children}</main>
      </div>
    </div>
  )
}
