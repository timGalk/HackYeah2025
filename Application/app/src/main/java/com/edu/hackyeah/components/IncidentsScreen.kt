package com.edu.hackyeah.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class Incident(
    val type: String,
    val location: String,
    val description: String,
    val time: String,
    val icon: ImageVector,
    val color: Color
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncidentsScreen(outerPadding: androidx.compose.foundation.layout.PaddingValues = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
    var showReportDialog by remember { mutableStateOf(false) }

    // Sample user-reported incidents
    val incidents = listOf(
        Incident(
            type = "Wypadek drogowy",
            location = "A4, Kraków - Katowice",
            description = "Kolizja 2 pojazdów, ruch ograniczony",
            time = "5 min temu",
            icon = Icons.Default.Warning,
            color = Color(0xFFD32F2F)
        ),
        Incident(
            type = "Korek",
            location = "Rondo Mogilskie, Kraków",
            description = "Duże natężenie ruchu",
            time = "15 min temu",
            icon = Icons.Default.Info,
            color = Color(0xFFF57C00)
        ),
        Incident(
            type = "Potrącenie",
            location = "ul. Wielicka, Kraków",
            description = "Potrącenie pieszego na przejściu",
            time = "1 godz. temu",
            icon = Icons.Default.Warning,
            color = Color(0xFFD32F2F)
        )
    )

    if (showReportDialog) {
        ReportIncidentDialog(
            onDismiss = { showReportDialog = false },
            onSuccess = {
                // Odśwież listę incydentów
            }
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(outerPadding)
            .background(Color(0xFFF5F5F5))
            .padding(16.dp)
    ) {
        // Simple Add Button
        Button(
            onClick = { showReportDialog = true },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1976D2)
            ),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(
                Icons.Default.Add,
                contentDescription = "Dodaj",
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                "Zgłoś incydent",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Incidents list
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(incidents.size) { index ->
                IncidentCard(incident = incidents[index])
            }
        }
    }
}

@Composable
fun IncidentCard(incident: Incident) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { /* TODO: Show incident details */ },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Icon
            Icon(
                incident.icon,
                contentDescription = null,
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(incident.color.copy(alpha = 0.1f))
                    .padding(12.dp),
                tint = incident.color
            )

            // Content
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = incident.type,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF212121)
                    )
                    Text(
                        text = incident.time,
                        fontSize = 12.sp,
                        color = Color(0xFF757575)
                    )
                }

                Text(
                    text = incident.location,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFF1976D2),
                    modifier = Modifier.padding(top = 4.dp)
                )

                Text(
                    text = incident.description,
                    fontSize = 14.sp,
                    color = Color(0xFF757575),
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}
