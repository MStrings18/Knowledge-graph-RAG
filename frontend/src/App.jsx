import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import userRouter from './Router/router.jsx'
import { RouterProvider } from 'react-router-dom'



function App() {
  

  return (
    <div>
      <RouterProvider router={userRouter} />
    </div>
  )
}

export default App
