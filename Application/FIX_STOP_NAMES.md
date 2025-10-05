# Problem: Wyświetlanie ID przystanków zamiast nazw

## Rozwiązanie

Problem polega na tym, że pliki JSON z mapowaniem przystanków nie zostały skopiowane do folderu `assets` aplikacji.

### Krok 1: Skopiuj pliki JSON

**WAŻNE:** Musisz uruchomić skrypt, który utworzyłem:

```
C:\Users\w1ndr\Documents\GitHub\HackYeah2025\Application\setup_assets.bat
```

Ten skrypt:
1. Utworzy folder `app/src/main/assets/`
2. Skopiuje `node_name_mapping.json` do assets
3. Skopiuje `node_name_mapping_reverse.json` do assets

### Krok 2: Przebuduj aplikację

Po skopiowaniu plików:
1. W Android Studio: **Build → Rebuild Project**
2. Odinstaluj starą wersję aplikacji z urządzenia/emulatora
3. Zainstaluj aplikację ponownie

### Jak to działa

Aplikacja teraz:
1. Ładuje `node_name_mapping.json` przy starcie
2. Konwertuje ID przystanków (np. `stop_937_130602`) na nazwy:
   - Wyciąga numer: `937`
   - Szuka w JSON: `"937": "Krowodrza"`
   - Wyświetla: **"Krowodrza"** zamiast `stop_937_130602`

### Logowanie diagnostyczne

Dodałem logowanie, aby sprawdzić, czy mapowanie działa:
- Sprawdź **Logcat** w Android Studio
- Szukaj wiadomości typu:
  ```
  Successfully loaded stop mappings from assets
  Mapped 937 -> Krowodrza
  ```
- Jeśli widzisz błędy typu:
  ```
  Error loading stop mappings
  No mapping found for ID: 937
  ```
  To znaczy, że pliki JSON nie zostały skopiowane lub są w złym formacie.

### Struktura pliku node_name_mapping.json

```json
{
  "937": "Krowodrza",
  "952": "Rondo Mogilskie",
  "101": "Cienista",
  ...
}
```

### Jeśli nadal widzisz ID zamiast nazw

1. Sprawdź czy folder `app/src/main/assets/` istnieje
2. Sprawdź czy pliki `node_name_mapping.json` i `node_name_mapping_reverse.json` są w tym folderze
3. Sprawdź Logcat czy są błędy przy ładowaniu plików
4. Upewnij się, że backend zwraca prawidłowe ID przystanków w formacie `stop_XXX_YYYYZZ`

## Testowanie

Przykładowe nazwy przystanków do wpisania:
- "Krowodrza"
- "Mistrzejowice"
- "Rondo Mogilskie"
- "Dworzec Główny"

Po wyszukaniu trasy powinieneś zobaczyć nazwy przystanków zamiast ID!

