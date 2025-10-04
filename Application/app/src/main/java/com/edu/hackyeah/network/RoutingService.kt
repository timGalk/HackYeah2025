package com.edu.hackyeah.network

import com.google.gson.annotations.SerializedName
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

// OSRM Response models
data class OSRMResponse(
    @SerializedName("routes") val routes: List<Route>?,
    @SerializedName("code") val code: String
)

data class Route(
    @SerializedName("geometry") val geometry: RouteGeometry?,
    @SerializedName("legs") val legs: List<RouteLeg>?,
    @SerializedName("distance") val distance: Double?,
    @SerializedName("duration") val duration: Double?
)

data class RouteGeometry(
    @SerializedName("coordinates") val coordinates: List<List<Double>>?
)

data class RouteLeg(
    @SerializedName("steps") val steps: List<RouteStep>?
)

data class RouteStep(
    @SerializedName("geometry") val geometry: RouteGeometry?,
    @SerializedName("maneuver") val maneuver: Maneuver?
)

data class Maneuver(
    @SerializedName("location") val location: List<Double>?
)

interface OSRMApi {
    @GET("route/v1/{profile}/{coordinates}")
    suspend fun getRoute(
        @Path("profile") profile: String = "driving",
        @Path("coordinates") coordinates: String,
        @Query("geometries") geometries: String = "geojson",
        @Query("overview") overview: String = "full"
    ): OSRMResponse
}

object RoutingService {
    private const val BASE_URL = "https://router.project-osrm.org/"

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

    private val api = retrofit.create(OSRMApi::class.java)

    suspend fun getRoutePoints(
        startLat: Double,
        startLon: Double,
        endLat: Double,
        endLon: Double,
        profile: String = "driving"
    ): List<Pair<Double, Double>>? {
        return try {
            val coordinates = "$startLon,$startLat;$endLon,$endLat"
            val response = api.getRoute(profile, coordinates)

            if (response.code == "Ok" && response.routes?.isNotEmpty() == true) {
                val route = response.routes.first()
                route.geometry?.coordinates?.map { cord ->
                    Pair(cord[1], cord[0]) // Convert [lon, lat] to (lat, lon)
                }
            } else {
                println("OSRM API returned code: ${response.code}")
                null
            }
        } catch (e: Exception) {
            println("Error getting route: ${e.message}")
            e.printStackTrace()
            null
        }
    }
}
