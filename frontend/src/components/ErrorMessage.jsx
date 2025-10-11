import React from 'react'

function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message">
      <div className="flex items-start space-x-3">
        <div className="text-xl">⚠️</div>
        <div className="flex-1">
          <h3 className="font-semibold text-red-800 mb-1">Something went wrong</h3>
          <p className="text-red-700 mb-3">{message}</p>
          {onRetry && (
            <button 
              onClick={onRetry}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ErrorMessage