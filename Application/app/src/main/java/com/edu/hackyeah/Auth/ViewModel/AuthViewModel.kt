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
        install(Auth) {
            alwaysAutoRefresh = true
            autoSaveToStorage = true
        }
    }

    private val _authState = MutableLiveData<AuthState>()
    val authState: MutableLiveData<AuthState> = _authState

    private val _userProfile = MutableLiveData<UserRecord?>()
    val userProfile: MutableLiveData<UserRecord?> = _userProfile

    init {
        Log.d(TAG, "AuthViewModel initialized")
        checkAuthState()
    }

    fun checkAuthState() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val session = supabase.auth.currentSessionOrNull()
                val user = session?.user

                if (user == null) {
                    Log.d(TAG, "No authenticated user")
                    _authState.postValue(AuthState.Unauthenticated)
                    _userProfile.postValue(null)
                    return@launch
                }

                val userId = user.id
                val userEmail = user.email ?: ""
                val userName = user.userMetadata?.get("name") as? String ?: "User"
                val userRole = user.userMetadata?.get("role") as? String ?: "user"

                Log.d(TAG, "Authenticated: $userEmail ($userId)")

                // Асинхронно, но гарантированно по порядку
                ensureUserRecordExists(userId, userEmail, userName, userRole)
                val profile = fetchUserProfileAsync(userId)

                _userProfile.postValue(profile)
                _authState.postValue(AuthState.Authenticated)
            } catch (e: Exception) {
                Log.e(TAG, "checkAuthState failed: ${e.message}")
                _authState.postValue(AuthState.Unauthenticated)
            }
        }
    }


    private suspend fun fetchUserProfileAsync(userId: String): UserRecord? {
        return try {
            val users = supabase.from("users")
                .select {
                    filter { eq("id", userId) }
                }.decodeList<UserRecord>()

            if (users.isNotEmpty()) {
                Log.d(TAG, "Fetched user profile for: $userId")
                users.first()
            } else {
                Log.w(TAG, "No profile found for: $userId")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to fetch user profile: ${e.message}")
            null
        }
    }



    fun refreshUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val session = supabase.auth.currentSessionOrNull()
                val userId = session?.user?.id
                if (userId != null) {
                    fetchUserProfile(userId)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to refresh user profile: ${e.message}")
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
                val session = supabase.auth.currentSessionOrNull()
                val userId = session?.user?.id
                val userEmail = session?.user?.email
                val userName = session?.user?.userMetadata?.get("name") as? String
                val userRole = session?.user?.userMetadata?.get("role") as? String ?: "user"

                // Only proceed if we have required user data
                if (userId != null && userEmail != null) {
                    ensureUserRecordExists(userId, userEmail, userName ?: "User", userRole)
                    fetchUserProfile(userId)
                }
                
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

        _authState.value = AuthState.Loading

        viewModelScope.launch(Dispatchers.IO) {
            try {
                supabase.auth.signUpWith(Email) {
                    this.email = email
                    this.password = password
                    data = JsonObject(mapOf("name" to JsonPrimitive(name), "role" to JsonPrimitive(role)))
                }


                val session = supabase.auth.currentSessionOrNull()
                val userId = session?.user?.id ?: return@launch
                val userEmail = session.user?.email ?: email


                supabase.auth.updateUser {
                    data = JsonObject(mapOf("name" to JsonPrimitive(name), "role" to JsonPrimitive(role)))
                }

                ensureUserRecordExists(userId, userEmail, name, role)
                val profile = fetchUserProfileAsync(userId)
                _userProfile.postValue(profile)

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
                _userProfile.postValue(null)
            } catch (e: Exception) {
                Log.e(TAG, "Sign-out failed: ${e.message}")
                _authState.postValue(AuthState.Error(e.message ?: "Sign-out failed"))
            }
        }
    }

    private suspend fun fetchUserProfile(userId: String?) {
        if (userId == null) {
            Log.w(TAG, "fetchUserProfile called with null userId")
            _userProfile.postValue(null)
            return
        }

        try {
            val users = supabase.from("users")
                .select {
                    filter {
                        eq("id", userId)
                    }
                }.decodeList<UserRecord>()

            if (users.isNotEmpty()) {
                Log.d(TAG, "User profile fetched for: $userId")
                _userProfile.postValue(users.first())
            } else {
                Log.w(TAG, "No user profile found for: $userId")
                _userProfile.postValue(null)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to fetch user profile: ${e.message}")
            _userProfile.postValue(null)
        }
    }

    private suspend fun ensureUserRecordExists(
        userId: String,
        email: String,
        name: String,
        role: String
    ) {
        try {
            val existing = supabase.from("users")
                .select {
                    filter { eq("id", userId) }
                }.decodeList<UserRecord>()

            if (existing.isEmpty()) {
                Log.d(TAG, "Creating user record for: $userId")
                supabase.from("users").insert(
                    UserRecord(
                        id = userId,
                        email = email,
                        name = name,
                        role = role
                    )
                )
                Log.d(TAG, "User record created for $email")
            } else {
                Log.d(TAG, "User record already exists for $userId")
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
