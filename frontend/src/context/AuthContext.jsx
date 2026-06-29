import { createContext, useContext, useState, useEffect } from 'react'
import axios from '../api/axios'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const userDataStr = localStorage.getItem('user')

    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      if (userDataStr) {
        try {
          const userData = JSON.parse(userDataStr)
          setUser(userData)
        } catch {
          localStorage.removeItem('user')
        }
      }
    } else {
      delete axios.defaults.headers.common['Authorization']
    }

    setLoading(false)
  }, [])

  const login = async (username, password) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const res = await axios.post('/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    const { access_token } = res.data
    const userData = { username, id: 1 }

    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify(userData))
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    setUser(userData)
  }

  const register = async (username, email, password) => {
    await axios.post('/register', { username, email, password })
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
