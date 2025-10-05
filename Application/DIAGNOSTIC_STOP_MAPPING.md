# Jak działa mapowanie nazw przystanków - diagnostyka

## Przepływ danych:

### 1. Użytkownik wpisuje nazwy (np. "Krowodrza" → "Mistrzejowice")

### 2. findNearestStopId() w LocationHelper
- Ładuje `node_name_mapping_reverse.json`
- Szuka nazwy "Krowodrza" → zwraca `stop_937_130602`
- Szuka nazwy "Mistrzejowice" → zwraca `stop_XXX_YYYYYY`

**Logcat pokaże:**
```
Searching route from: Krowodrza to: Mistrzejowice
Found stop IDs: source=stop_937_130602, target=stop_XXX_YYYYYY
```

### 3. TransportRouteService.getTransportRoute()
- Wysyła request do API: `GET /api/v1/transport/routes?source=stop_937_130602&target=stop_XXX_YYYYYY`
- Otrzymuje odpowiedź z listą nodes i segments

**Logcat pokaże:**
```
Got response from API: incident=false
Processing 68 nodes and 67 segments
```

### 4. TransportRouteService.getStopName()
- Dla każdego node (np. `stop_937_130602`):
  - Wyciąga `937` (numeric ID)
  - Szuka w `node_name_mapping.json`: `"937": "Krowodrza"`
  - Zwraca `"Krowodrza"`

**Logcat pokaże:**
```
Mapped 937 -> Krowodrza
First stop: stop_937_130602 -> Krowodrza
Stop 0: stop_935_130302 -> Przystanek1 (route: 301)
Stop 1: stop_909_127701 -> Przystanek2 (route: 221)
...
Created 68 destination points
```

### 5. RouteTile wyświetla
- `destinationPoints.first().name` = **"Krowodrza"** (nie `stop_937_130602`)
- `destinationPoints.last().name` = **"Mistrzejowice"** (nie `stop_XXX_YYYYYY`)

## ⚠️ Jeśli nadal widzisz ID zamiast nazw:

### Sprawdź Logcat - szukaj tych wiadomości:

#### ✅ Sukces - pliki załadowane:
```
Successfully loaded stop mappings from assets
Mapped 937 -> Krowodrza
Mapped 935 -> Nazwa Przystanku
```

#### ❌ Problem 1 - brak plików JSON:
```
Error loading stop mappings: node_name_mapping.json (No such file or directory)
```
**Rozwiązanie:** Uruchom `setup_assets.bat`

#### ❌ Problem 2 - brak mapowania:
```
No mapping found for ID: 937 (from stop_937_130602)
Available mappings: null
```
**Rozwiązanie:** Plik JSON nie został poprawnie załadowany lub jest pusty

#### ❌ Problem 3 - nie można wyciągnąć ID:
```
Failed to extract numeric ID from: stop_937_130602
```
**Rozwiązanie:** Format ID jest nieprawidłowy (powinien być `stop_XXX_YYYYZZ`)

## Krok po kroku testowanie:

1. **Uruchom aplikację**
2. **Otwórz Logcat** (Android Studio → Logcat)
3. **Filtruj** po "System.out" lub wyszukaj "Successfully loaded"
4. **Wpisz nazwy przystanków** (np. "Krowodrza" → "Mistrzejowice")
5. **Kliknij "Znajdź trasę"**
6. **Sprawdź logi** - powinny pojawić się wszystkie wiadomości diagnostyczne

## Struktura plików JSON:

### node_name_mapping.json (ID → Nazwa)
```json
{
  "101": "Cienista",
  "937": "Krowodrza",
  "952": "Rondo Mogilskie"
}
```

### node_name_mapping_reverse.json (Nazwa → ID)
```json
{
  "Cienista": "stop_571_303729",
  "Krowodrza": "stop_937_130602",
  "Rondo Mogilskie": "stop_952_132601"
}
```

## Jeśli wszystko działa prawidłowo:

**W RouteTile zobaczysz:**
```
🟢 Krowodrza → 🔴 Mistrzejowice
```

**Zamiast:**
```
🟢 stop_937_130602 → 🔴 stop_271_37505
```

## Dodatkowe kroki diagnostyczne:

1. Sprawdź czy folder `app/src/main/assets/` istnieje
2. Sprawdź czy pliki JSON są w tym folderze
3. Zrób Clean Build: **Build → Clean Project** → **Build → Rebuild Project**
4. Odinstaluj aplikację i zainstaluj ponownie
5. Sprawdź logi od początku uruchomienia aplikacji

