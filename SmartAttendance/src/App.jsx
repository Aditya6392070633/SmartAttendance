import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import SmartAttendance from './SmartAttendance'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      

      <SmartAttendance/>
    </>
  )
}

export default App
