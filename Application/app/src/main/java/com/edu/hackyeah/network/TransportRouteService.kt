package com.edu.hackyeah.network

import com.google.gson.annotations.SerializedName
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Query

// Response models for transport API
data class TransportRouteResponse(
    @SerializedName("incident_detected") val incidentDetected: Boolean,
    @SerializedName("message") val message: String?,
    @SerializedName("default_path") val defaultPath: TransportPath?,
    @SerializedName("suggested_path") val suggestedPath: TransportPath?
)

data class TransportPath(
    @SerializedName("nodes") val nodes: List<String>,
    @SerializedName("segments") val segments: List<RouteSegment>,
    @SerializedName("total_default_weight") val totalDefaultWeight: Int,
    @SerializedName("total_current_weight") val totalCurrentWeight: Int
)

data class RouteSegment(
    @SerializedName("source") val source: String,
    @SerializedName("target") val target: String,
    @SerializedName("key") val key: String,
    @SerializedName("mode") val mode: String,
    @SerializedName("default_weight") val defaultWeight: Int,
    @SerializedName("current_weight") val currentWeight: Int,
    @SerializedName("impacted") val impacted: Boolean,
    @SerializedName("distance_km") val distanceKm: Double?,
    @SerializedName("speed_kmh") val speedKmh: Double?,
    @SerializedName("connector") val connector: String?,
    @SerializedName("metadata") val metadata: SegmentMetadata?
)

data class SegmentMetadata(
    @SerializedName("trip_id") val tripId: String?,
    @SerializedName("route_id") val routeId: String?,
    @SerializedName("route_short_name") val routeShortName: String?,
    @SerializedName("route_long_name") val routeLongName: String?
)

// Stop name mapping data
data class StopMapping(
    val stopId: String,
    val name: String
)

interface TransportApi {
    @GET("api/v1/transport/routes")
    suspend fun getRoute(
        @Query("mode") mode: String,
        @Query("source") source: String,
        @Query("target") target: String
    ): TransportRouteResponse
}

object TransportRouteService {
    private const val BASE_URL = "http://10.0.2.2:8000/" // For Android emulator (localhost)
    // Use "http://localhost:8000/" for physical device on same network

    private val okHttpClient = okhttp3.OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    private val api = retrofit.create(TransportApi::class.java)

    // Cache for stop name mappings
    private var stopNameMapping: Map<String, String>? = null

    fun loadStopMappings(mappingJson: String) {
        try {
            val gson = com.google.gson.Gson()
            val type = object : com.google.gson.reflect.TypeToken<Map<String, String>>() {}.type
            stopNameMapping = gson.fromJson(mappingJson, type)
        } catch (e: Exception) {
            println("Error loading stop mappings: ${e.message}")
        }
    }

    fun getStopName(stopId: String): String {
        // Extract the numeric ID from stop_XXX_YYYYZZ format
                val numericId = stopId.split("_").getOrNull(1) ?: run {
            println("Failed to extract numeric ID from: $stopId")
            return stopId
        }

        val name = stopNameMapping?.get(numericId)

        if (name == null) {
            println("No mapping found for ID: $numericId (from $stopId)")
            println("Available mappings: ${stopNameMapping?.keys?.take(5)}")
        } else {
            println("Mapped $numericId -> $name")
        }

        return name ?: stopId
    }

    suspend fun getTransportRoute(
        mode: String = "bus",
        sourceStopId: String,
        targetStopId: String
    ): TransportRouteResponse? {
        return try {
            api.getRoute(mode, sourceStopId, targetStopId)
        } catch (e: Exception) {
            println("Error getting transport route: ${e.message}")
            e.printStackTrace()
            null
        }
    }
}
