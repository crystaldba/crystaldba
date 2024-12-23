package middleware

import (
	"net/http"
)

type AuthMiddleware struct {
	accessKey            string
	forceBypassAccessKey bool
}

func NewAuthMiddleware(accessKey string, forceBypassAccessKey bool) *AuthMiddleware {
	return &AuthMiddleware{
		accessKey:            accessKey,
		forceBypassAccessKey: forceBypassAccessKey,
	}
}

func (a *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Only authenticate requests to /api paths
		if !a.forceBypassAccessKey && len(r.URL.Path) >= 4 && r.URL.Path[:4] == "/api" {
			authHeader := r.Header.Get("Crystaldba-Access-Key")
			if authHeader == "" {
				http.Error(w, "Unauthorized - Missing Crystaldba-Access-Key header", http.StatusUnauthorized)
				return
			}

			if authHeader != a.accessKey {
				http.Error(w, "Unauthorized - Invalid Crystaldba-Access-Key", http.StatusUnauthorized)
				return
			}
		}

		next.ServeHTTP(w, r)
	})
}
