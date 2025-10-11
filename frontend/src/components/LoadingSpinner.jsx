import React from 'react'

function LoadingSpinner({ 
  size = 'medium', 
  message = 'Loading...', 
  variant = 'loading' 
}) {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8', 
    large: 'w-12 h-12'
  }

  const variantStyles = {
    loading: {
      borderColor: 'border-primary-200',
      spinColor: 'border-t-primary-600',
      textColor: 'text-gray-600',
      animation: 'animate-spin',
      icon: '⏳'
    },
    reconnecting: {
      borderColor: 'border-yellow-200',
      spinColor: 'border-t-yellow-600',
      textColor: 'text-yellow-600',
      animation: 'animate-spin',
      icon: '🔄'
    },
    error: {
      borderColor: 'border-red-200',
      spinColor: 'border-t-red-600',
      textColor: 'text-red-600',
      animation: 'animate-pulse',
      icon: '⚠️'
    }
  }

  const style = variantStyles[variant]

  return (
    <div className="flex flex-col items-center justify-center space-y-3 p-4">
      <div className="relative">
        <div className={`
          ${sizeClasses[size]} 
          ${style.borderColor} 
          ${style.spinColor} 
          ${style.animation}
          border-4 rounded-full
        `}></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs">{style.icon}</span>
        </div>
      </div>
      {message && (
        <p className={`text-sm ${style.textColor} text-center`}>
          {message}
        </p>
      )}
    </div>
  )
}

export default LoadingSpinner