package com.edu.hackyeah.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edu.hackyeah.location.DestinationPoint
import java.time.Duration
import java.time.format.DateTimeFormatter

@Composable
fun RouteTile(
    destinationPoints: List<DestinationPoint>,
    onClick: () -> Unit = {}
) {
    if (destinationPoints.isEmpty()) return

    val startPoint = destinationPoints.first()
    val endPoint = destinationPoints.last()

    // Calculate driving time
    val duration = Duration.between(startPoint.arrivalTime, endPoint.arrivalTime)
    val hours = duration.toHours()
    val minutes = duration.toMinutes() % 60

    val drivingTime = when {
        hours > 0 -> "${hours}h ${minutes}min"
        else -> "${minutes}min"
    }

    // Format arrival time
    val timeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    val arrivalTimeFormatted = endPoint.arrivalTime.atZone(java.time.ZoneId.systemDefault()).format(timeFormatter)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            Text(
                text = "Twoja trasa",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF1976D2)
            )

            // Route info
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Start location
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(
                        Icons.Default.Place,
                        contentDescription = null,
                        tint = Color(0xFF4CAF50),
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = startPoint.name,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

                // Arrow
                Icon(
                    Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = null,
                    tint = Color(0xFF757575),
                    modifier = Modifier.size(24.dp)
                )

                // End location
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.End
                ) {
                    Text(
                        text = endPoint.name,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Icon(
                        Icons.Default.Place,
                        contentDescription = null,
                        tint = Color(0xFFF44336),
                        modifier = Modifier.size(24.dp)
                    )
                }
            }

            // Driving time and arrival info
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Czas jazdy",
                        fontSize = 12.sp,
                        color = Color(0xFF757575)
                    )
                    Text(
                        text = drivingTime,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF1976D2)
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Przyjazd",
                        fontSize = 12.sp,
                        color = Color(0xFF757575)
                    )
                    Text(
                        text = arrivalTimeFormatted,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF1976D2)
                    )
                }
            }

            // Number of stops
            if (destinationPoints.size > 2) {
                Text(
                    text = "${destinationPoints.size - 2} przystanków po drodze",
                    fontSize = 12.sp,
                    color = Color(0xFF757575)
                )
            }
        }
    }
}
