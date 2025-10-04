package com.edu.hackyeah.network

import com.google.gson.annotations.SerializedName
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

data class IncidentRequest(
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("description") val description: String,
    @SerializedName("category") val category: String,
    @SerializedName("username") val username: String
)

data class IncidentResponse(
    @SerializedName("id") val id: String?,
    @SerializedName("message") val message: String?
)

interface IncidentApi {
    @POST("api/v1/incidents")
    suspend fun reportIncident(@Body request: IncidentRequest): IncidentResponse
}

object IncidentService {
    // Use 10.0.2.2 for Android Emulator to access localhost
    // Use actual IP address if testing on physical device
    private const val BASE_URL = "http://10.0.2.2:8000/"

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    private val api = retrofit.create(IncidentApi::class.java)

    suspend fun reportIncident(
        latitude: Double,
        longitude: Double,
        description: String,
        category: String,
        username: String = "janedoe"
    ): Result<IncidentResponse> {
        return try {
            val request = IncidentRequest(
                latitude = latitude,
                longitude = longitude,
                description = description,
                category = category,
                username = username
            )
            println("Sending incident request to: ${BASE_URL}api/v1/incidents")
            println("Request: $request")
            val response = api.reportIncident(request)
            println("Response: $response")
            Result.success(response)
        } catch (e: Exception) {
            println("Error reporting incident: ${e.message}")
            e.printStackTrace()
            Result.failure(e)
        }
    }
}
