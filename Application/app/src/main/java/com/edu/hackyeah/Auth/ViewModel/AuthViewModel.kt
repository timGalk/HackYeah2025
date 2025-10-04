package com.edu.hackyeah.Auth.ViewModel

import android.util.Log
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.github.jan.supabase.SupabaseClient
import io.github.jan.supabase.createSupabaseClient
import io.github.jan.supabase.gotrue.Auth
import io.github.jan.supabase.gotrue.auth
import io.github.jan.supabase.gotrue.providers.builtin.Email
import io.github.jan.supabase.postgrest.Postgrest
import io.github.jan.supabase.postgrest.from
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

private const val TAG = "AuthViewModel"

class AuthViewModel : ViewModel() {

    private val supabase: SupabaseClient = createSupabaseClient(
        supabaseUrl = "https://nimyeezxxgrnudnvnpsa.supabase.co",
        supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5pbXllZXp4eGdybnVkbnZucHNhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1OTc3NjQsImV4cCI6MjA3NTE3Mzc2NH0.e1-fLcnTwSYVUCJNXMzF7eKpr2XDJNEWUKLdVOtKaNM"
    ) {
        install(Auth)
        install(Postgrest)
    }

    private val _authState = MutableLiveData<AuthState>()
    val authState: MutableLiveData<AuthState> = _authState

    init {
        Log.d(TAG, "AuthViewModel initialized")
        checkAuthState()
    }

    private fun checkAuthState() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val session = supabase.auth.currentSessionOrNull()
                if (session == null) {
                    Log.d(TAG, "No authenticated user found")
                    _authState.postValue(AuthState.Unauthenticated)
                } else {
                    Log.d(TAG, "Authenticated user found: ${session.user?.email}")
                    val userId = session.user?.id
                    val userEmail = session.user?.email
                    val userName = session.user?.userMetadata?.get("name") as? String
                    val userRole = session.user?.userMetadata?.get("role") as? String ?: "user"
                    ensureUserRecordExists(userId, userEmail, userName, userRole)
                    _authState.postValue(AuthState.Authenticated)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error checking auth state: ${e.message}")
                _authState.postValue(AuthState.Unauthenticated)
            }
        }
    }

    fun login(email: String, password: String) {
        Log.d(TAG, "Attempting to log in with email: $email")

        if (email.isEmpty() || password.isEmpty()) {
            _authState.value = AuthState.Error("Fields cannot be empty")
            return
        }

        _authState.value = AuthState.Loading

        viewModelScope.launch(Dispatchers.IO) {
            try {
                supabase.auth.signInWith(Email) {
                    this.email = email
                    this.password = password
                }
                Log.d(TAG, "Login successful for $email")
                val session = supabase.auth.currentSessionOrNull()
                val userId = session?.user?.id
                val userEmail = session?.user?.email
                val userName = session?.user?.userMetadata?.get("name") as? String
                val userRole = session?.user?.userMetadata?.get("role") as? String ?: "user"
                ensureUserRecordExists(userId, userEmail, userName, userRole)
                _authState.postValue(AuthState.Authenticated)
            } catch (e: Exception) {
                Log.e(TAG, "Login failed: ${e.message}")
                _authState.postValue(AuthState.Error(e.message ?: "Login failed"))
            }
        }
    }

    fun signUp(email: String, password: String, name: String, role: String = "user") {
        Log.d(TAG, "Attempting to sign up with email: $email, name: $name, role: $role")

        if (email.isEmpty() || password.isEmpty() || name.isEmpty()) {
            _authState.value = AuthState.Error("Fields cannot be empty")
            return
        }

        if (role !in listOf("user", "admin")) {
            _authState.value = AuthState.Error("Invalid role specified")
            return
        }

        _authState.value = AuthState.Loading

        viewModelScope.launch(Dispatchers.IO) {
            try {
                supabase.auth.signUpWith(Email) {
                    this.email = email
                    this.password = password
                    data = JsonObject(mapOf("name" to JsonPrimitive(name), "role" to JsonPrimitive(role)))
                }
                Log.d(TAG, "User sign-up successful for: $email with role: $role")
                val session = supabase.auth.currentSessionOrNull()
                ensureUserRecordExists(session?.user?.id, session?.user?.email, name, role)
                _authState.postValue(AuthState.Authenticated)
            } catch (e: Exception) {
                Log.e(TAG, "Sign-up failed: ${e.message}")
                _authState.postValue(AuthState.Error(e.message ?: "Sign-up failed"))
            }
        }
    }

    fun signOut() {
        Log.d(TAG, "Signing out user...")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                supabase.auth.signOut()
                _authState.postValue(AuthState.Unauthenticated)
            } catch (e: Exception) {
                Log.e(TAG, "Sign-out failed: ${e.message}")
                _authState.postValue(AuthState.Error(e.message ?: "Sign-out failed"))
            }
        }
    }

    private suspend fun ensureUserRecordExists(userId: String?, email: String?, name: String?, role: String?) {
        if (userId == null || email == null) {
            Log.w(TAG, "ensureUserRecordExists called with null userId/email")
            return
        }

        try {
            val existing = supabase.from("users")
                .select {
                    filter {
                        eq("id", userId)
                    }
                }.decodeList<UserRecord>()

            if (existing.isEmpty()) {
                Log.d(TAG, "Creating new user record for: $userId with role: $role")
                supabase.from("users").insert(
                    UserRecord(
                        id = userId,
                        email = email,
                        name = name ?: "",
                        role = role ?: "user"
                    )
                )
            } else {
                Log.d(TAG, "User record already exists for: $userId")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to ensure user record exists: ${e.message}")
        }
    }
}

@Serializable
data class UserRecord(
    val id: String,
    val email: String,
    val name: String = "",
    val role: String = "user"
)

sealed class AuthState {
    object Authenticated : AuthState()
    object Unauthenticated : AuthState()
    object Loading : AuthState()
    data class Error(val message: String) : AuthState()
}
