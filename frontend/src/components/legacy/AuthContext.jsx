import React, { createContext, useContext, useState, useEffect } from 'react'
import { 
  getCurrentUser, 
  login as loginAPI, 
  register as registerAPI, 
  linkSleeperAccount as linkSleeperAPI,
  logout as logoutAPI,
  getToken 
} from '../services/api'

const AuthContext = createContext({
  user: null,
  loading: true,
  isAuthenticated: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  linkSleeper: async () => {}
})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Check for existing authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = getToken()
        if (token) {
          const userData = await getCurrentUser()
          setUser(userData)
          setIsAuthenticated(true)
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        // Token might be invalid, clear it
        logoutAPI()
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = async (email, password) => {
    try {
      setLoading(true)
      const tokenResponse = await loginAPI(email, password)
      
      // Get user data
      const userData = await getCurrentUser()
      setUser(userData)
      setIsAuthenticated(true)
      
      return { success: true, data: tokenResponse }
    } catch (error) {
      console.error('Login failed:', error)
      return { success: false, error: error.message }
    } finally {
      setLoading(false)
    }
  }

  const register = async (email, password, confirmPassword) => {
    try {
      setLoading(true)
      const tokenResponse = await registerAPI(email, password, confirmPassword)
      
      // Get user data
      const userData = await getCurrentUser()
      setUser(userData)
      setIsAuthenticated(true)
      
      return { success: true, data: tokenResponse }
    } catch (error) {
      console.error('Registration failed:', error)
      return { success: false, error: error.message }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    setIsAuthenticated(false)
    logoutAPI()
  }

  const linkSleeper = async (sleeperUsername) => {
    try {
      const updatedUser = await linkSleeperAPI(sleeperUsername)
      setUser(updatedUser)
      
      return { success: true, data: updatedUser }
    } catch (error) {
      console.error('Sleeper linking failed:', error)
      return { success: false, error: error.message }
    }
  }

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    linkSleeper
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}