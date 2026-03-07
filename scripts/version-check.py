#!/usr/bin/env python3
"""
Version Check Script für Kaffeemaschinen-Integration

Dieses Script überprüft die Konsistenz zwischen Git-Tags und der Version
in der manifest.json Datei. Es folgt dem Semantic Versioning 2.0.0 Standard.

Exit Codes:
- 0: Versionen sind konsistent
- 1: Versionen sind inkonsistent oder Fehler aufgetreten
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import Optional, Tuple


class VersionChecker:
    """Klasse zur Überprüfung der Versionskonsistenz zwischen Git-Tags und manifest.json"""
    
    def __init__(self, manifest_path: str = "custom_components/kaffeemaschine/manifest.json"):
        self.manifest_path = Path(manifest_path)
        self.semver_pattern = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$')
    
    def get_manifest_version(self) -> Optional[str]:
        """
        Extrahiert die Version aus der manifest.json Datei.
        
        Returns:
            str: Version aus manifest.json oder None bei Fehler
        """
        try:
            if not self.manifest_path.exists():
                print(f"❌ Fehler: manifest.json nicht gefunden unter {self.manifest_path}")
                return None
            
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            version = manifest_data.get('version')
            if not version:
                print("❌ Fehler: Keine Version in manifest.json gefunden")
                return None
            
            print(f"📄 Manifest Version: {version}")
            return version
            
        except json.JSONDecodeError as e:
            print(f"❌ Fehler beim Parsen der manifest.json: {e}")
            return None
        except Exception as e:
            print(f"❌ Fehler beim Lesen der manifest.json: {e}")
            return None
    
    def get_latest_git_tag(self) -> Optional[str]:
        """
        Ermittelt den neuesten Git-Tag.
        
        Returns:
            str: Neuester Git-Tag oder None bei Fehler
        """
        try:
            # Versuche den neuesten Tag zu finden
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                capture_output=True,
                text=True,
                check=True
            )
            
            tag = result.stdout.strip()
            if tag:
                print(f"🏷️  Neuester Git-Tag: {tag}")
                return tag
            else:
                print("⚠️  Warnung: Keine Git-Tags gefunden")
                return None
                
        except subprocess.CalledProcessError as e:
            if e.returncode == 128:
                print("⚠️  Warnung: Keine Git-Tags gefunden oder nicht in einem Git-Repository")
            else:
                print(f"❌ Fehler beim Abrufen der Git-Tags: {e}")
            return None
        except FileNotFoundError:
            print("❌ Fehler: Git ist nicht installiert oder nicht im PATH")
            return None
    
    def parse_version(self, version: str) -> Optional[Tuple[int, int, int, str, str]]:
        """
        Parst eine Versionsnummer nach Semantic Versioning 2.0.0.
        
        Args:
            version: Versionsnummer als String
            
        Returns:
            Tuple: (major, minor, patch, prerelease, build) oder None bei ungültiger Version
        """
        match = self.semver_pattern.match(version)
        if not match:
            return None
        
        major, minor, patch, prerelease, build = match.groups()
        return (
            int(major),
            int(minor), 
            int(patch),
            prerelease or "",
            build or ""
        )
    
    def normalize_version(self, version: str) -> str:
        """
        Normalisiert eine Versionsnummer (entfernt 'v' Präfix falls vorhanden).
        
        Args:
            version: Versionsnummer als String
            
        Returns:
            str: Normalisierte Versionsnummer
        """
        return version.lstrip('v')
    
    def compare_versions(self, manifest_version: str, git_tag: str) -> bool:
        """
        Vergleicht die Versionen aus manifest.json und Git-Tag.
        
        Args:
            manifest_version: Version aus manifest.json
            git_tag: Git-Tag Version
            
        Returns:
            bool: True wenn Versionen konsistent sind, False sonst
        """
        # Normalisiere beide Versionen
        normalized_manifest = self.normalize_version(manifest_version)
        normalized_tag = self.normalize_version(git_tag)
        
        print(f"🔍 Vergleiche Versionen:")
        print(f"   Manifest: {normalized_manifest}")
        print(f"   Git-Tag:  {normalized_tag}")
        
        # Parse beide Versionen
        manifest_parsed = self.parse_version(normalized_manifest)
        tag_parsed = self.parse_version(normalized_tag)
        
        if not manifest_parsed:
            print(f"❌ Ungültige Versionsnummer in manifest.json: {normalized_manifest}")
            return False
        
        if not tag_parsed:
            print(f"❌ Ungültiger Git-Tag: {normalized_tag}")
            return False
        
        # Vergleiche die Versionen
        if manifest_parsed[:3] == tag_parsed[:3]:  # Vergleiche nur major.minor.patch
            print("✅ Versionen sind konsistent!")
            return True
        else:
            print("❌ Versionen sind inkonsistent!")
            print(f"   Manifest: {manifest_parsed[0]}.{manifest_parsed[1]}.{manifest_parsed[2]}")
            print(f"   Git-Tag:  {tag_parsed[0]}.{tag_parsed[1]}.{tag_parsed[2]}")
            return False
    
    def check_version_consistency(self) -> bool:
        """
        Hauptmethode zur Überprüfung der Versionskonsistenz.
        
        Returns:
            bool: True wenn alle Versionen konsistent sind, False sonst
        """
        print("🔄 Starte Version-Check...")
        print("=" * 50)
        
        # Hole manifest.json Version
        manifest_version = self.get_manifest_version()
        if not manifest_version:
            return False
        
        # Hole neuesten Git-Tag
        git_tag = self.get_latest_git_tag()
        if not git_tag:
            print("⚠️  Warnung: Kein Git-Tag gefunden. Überspringe Vergleich.")
            print("💡 Tipp: Erstelle einen Git-Tag mit: git tag v" + manifest_version)
            return False
        
        # Vergleiche Versionen
        print("-" * 30)
        return self.compare_versions(manifest_version, git_tag)


def main():
    """Hauptfunktion des Scripts"""
    checker = VersionChecker()
    
    try:
        is_consistent = checker.check_version_consistency()
        
        print("=" * 50)
        if is_consistent:
            print("🎉 Version-Check erfolgreich abgeschlossen!")
            sys.exit(0)
        else:
            print("💥 Version-Check fehlgeschlagen!")
            print("\n📋 Mögliche Lösungen:")
            print("   1. Aktualisiere die Version in manifest.json")
            print("   2. Erstelle einen neuen Git-Tag mit der korrekten Version")
            print("   3. Überprüfe die Semantic Versioning Konventionen")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Version-Check abgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()