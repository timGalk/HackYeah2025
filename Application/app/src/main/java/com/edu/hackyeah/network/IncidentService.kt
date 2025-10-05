package com.edu.hackyeah.network

import com.google.gson.annotations.SerializedName
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

data class IncidentRequest(
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("description") val description: String,
    @SerializedName("category") val category: String,
    @SerializedName("username") val username: String
)

// Wrapper for list responses: { "incidents": [ ... ] }
data class IncidentsListResponse(
    @SerializedName("incidents") val incidents: List<IncidentItem>
)

data class IncidentResponse(
    @SerializedName("id") val id: String?,
    @SerializedName("message") val message: String?
)

// Item returned by GET endpoints
data class IncidentItem(
    @SerializedName("id") val id: String? = null,
    @SerializedName("category") val category: String? = null,
    @SerializedName("description") val description: String? = null,
    @SerializedName("latitude") val latitude: Double? = null,
    @SerializedName("longitude") val longitude: Double? = null,
    @SerializedName("username") val username: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("approved") val approved: Boolean? = null
)

interface IncidentApi {
    @POST("api/v1/incidents")
    suspend fun reportIncident(@Body request: IncidentRequest): IncidentResponse

    @GET("api/v1/incidents")
    suspend fun getAllIncidents(): IncidentsListResponse

    @GET("api/v1/incidents/latest")
    suspend fun getLatestIncidents(@Query("limit") limit: Int = 10): IncidentsListResponse

    // New: filter by multiple coordinates and distance
    @GET("api/v1/incidents")
    suspend fun getIncidentsByCoordinates(
        @Query("coordinates") coordinates: List<String>,
        @Query("max_distance_km") maxDistanceKm: Double
    ): IncidentsListResponse
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

    suspend fun fetchAllIncidents(): Result<List<IncidentItem>> {
        return try {
            val resp = api.getAllIncidents()
            Result.success(resp.incidents)
        } catch (e: Exception) {
            println("Error fetching all incidents: ${e.message}")
            e.printStackTrace()
            Result.failure(e)
        }
    }

    suspend fun fetchLatestIncidents(limit: Int = 10): Result<List<IncidentItem>> {
        val safeLimit = limit.coerceIn(1, 1000)
        return try {
            val resp = api.getLatestIncidents(safeLimit)
            Result.success(resp.incidents)
        } catch (e: Exception) {
            println("Error fetching latest incidents: ${e.message}")
            e.printStackTrace()
            Result.failure(e)
        }
    }

    suspend fun fetchIncidentsByCoordinates(
        coordinates: List<Pair<Double, Double>>,
        maxDistanceKm: Double = 1.0
    ): Result<List<IncidentItem>> {
        return try {
            val coordParams = coordinates.map { (lat, lon) -> "${lat},${lon}" }
            val resp = api.getIncidentsByCoordinates(coordParams, maxDistanceKm)
            Result.success(resp.incidents)
        } catch (e: Exception) {
            println("Error fetching incidents by coordinates: ${e.message}")
            e.printStackTrace()
            Result.failure(e)
        }
    }
}
