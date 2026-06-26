import { createContext, useContext, useState, useEffect } from 'react'
import axios from '../api/axios'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      const userDataStr = localStorage.getItem('user')
      if (userDataStr) {
        const userData = JSON.parse(userDataStr)
        setUser(userData)
      }
    }
    setLoading(false)
  }, [])

  const login = async (username, password) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const res = await axios.post('/login', formData)
    const { access_token } = res.data
    localStorage.setItem('token', access_token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    
    const userData = { username, id: 1 } // Use dummy user for now
    setUser(userData)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const register = async (username, email, password) => {
    const res = await axios.post('/register', { username, email, password })
    // Auto login after register
    await login(username, password)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
