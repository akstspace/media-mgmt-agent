"""
Media Management Tools for Radarr and Sonarr

This module provides RequestsTool instances for interacting with Radarr and Sonarr APIs.
Configure the base URLs and API keys before using these tools.

Usage:
    # Set your configuration
    from media_tools import configure_radarr, get_radarr_tools
    
    configure_radarr("http://localhost:7878", "your_api_key_here")
    tools = get_radarr_tools()

    # Use with agent
    for tool in tools:
        agent.register_tool(tool)
"""

import json
from typing import Any, Dict, List
from acton_agent.tools import RequestsTool

RADARR_URL = None
RADARR_API_KEY = None
SONARR_URL = None
SONARR_API_KEY = None


# =============================================================================
# RADARR CUSTOM TOOL CLASSES WITH OUTPUT POST-PROCESSING
# =============================================================================

class RadarrMovieListTool(RequestsTool):
    """Custom tool for listing Radarr movies with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert movie list output to Markdown table based on MovieResource schema."""
        try:
            movies = json.loads(output)
            if not isinstance(movies, list):
                return output
            
            if not movies:
                return "# 📽️ Radarr Movie Library\n\n*No movies found in library.*"
            
            # Build Markdown table
            md = "# 📽️ Radarr Movie Library\n\n"
            md += "| ID | Title | Year | Status | Monitored | Downloaded | File Size | Quality | TMDB | IMDB |\n"
            md += "|---:|:---|:---:|:---|:---:|:---:|---:|:---|:---:|:---|\n"
            
            total_size = 0
            for movie in movies:
                movie_id = movie.get('id', 'N/A')
                title = movie.get('title', 'Unknown')
                year = movie.get('year', 'N/A')
                status = movie.get('status', 'Unknown')
                monitored = '✅' if movie.get('monitored') else '❌'
                has_file = '✅' if movie.get('hasFile') else '❌'
                
                # File size from MovieResource
                size_on_disk = movie.get('sizeOnDisk', 0)
                if size_on_disk:
                    size_gb = round(size_on_disk / (1024**3), 2)
                    total_size += size_on_disk
                    size_str = f"{size_gb} GB"
                else:
                    size_str = "-"
                
                # Get quality from movie file
                quality = "-"
                movie_file = movie.get('movieFile', {})
                if movie_file:
                    quality_info = movie_file.get('quality', {}).get('quality', {})
                    quality = quality_info.get('name', '-')
                
                tmdb_id = movie.get('tmdbId', 'N/A')
                imdb_id = movie.get('imdbId', 'N/A')
                
                md += f"| {movie_id} "
                md += f"| {title} "
                md += f"| {year} "
                md += f"| {status} "
                md += f"| {monitored} "
                md += f"| {has_file} "
                md += f"| {size_str} "
                md += f"| {quality} "
                md += f"| {tmdb_id} "
                md += f"| {imdb_id} |\n"
            
            downloaded = sum(1 for m in movies if m.get('hasFile'))
            total_size_gb = round(total_size / (1024**3), 2)
            
            md += f"\n---\n\n"
            md += f"**📊 Summary:** {len(movies)} movies total • {downloaded} downloaded ({round(downloaded/len(movies)*100, 1)}%) • {total_size_gb} GB total\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


class RadarrMovieDetailTool(RequestsTool):
    """Custom tool for getting Radarr movie details with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert movie detail output to formatted Markdown based on MovieResource schema."""
        try:
            movie = json.loads(output)
            if not isinstance(movie, dict):
                return output
            
            # Build comprehensive Markdown output
            title = movie.get('title', 'Unknown Movie')
            year = movie.get('year', 'N/A')
            md = f"# 🎬 {title} ({year})\n\n"
            
            # Overview section
            md += "## 📋 Overview\n\n"
            overview = movie.get('overview', 'No overview available.')
            md += f"{overview}\n\n"
            
            # Basic Information
            md += "## ℹ️ Information\n\n"
            md += f"- **Radarr ID:** {movie.get('id', 'N/A')}\n"
            md += f"- **Status:** {movie.get('status', 'Unknown')}\n"
            md += f"- **Original Title:** {movie.get('originalTitle', 'N/A')}\n"
            md += f"- **Studio:** {movie.get('studio', 'Unknown')}\n"
            md += f"- **Runtime:** {movie.get('runtime', 0)} minutes\n"
            md += f"- **Certification:** {movie.get('certification', 'Not Rated')}\n\n"
            
            # External IDs
            md += "## 🔗 External IDs\n\n"
            md += f"- **TMDB ID:** {movie.get('tmdbId', 'N/A')}\n"
            md += f"- **IMDB ID:** {movie.get('imdbId', 'N/A')}\n\n"
            
            # Release Dates from MovieResource
            md += "## 📅 Release Information\n\n"
            if movie.get('inCinemas'):
                md += f"- **In Cinemas:** {movie.get('inCinemas')}\n"
            if movie.get('digitalRelease'):
                md += f"- **Digital Release:** {movie.get('digitalRelease')}\n"
            if movie.get('physicalRelease'):
                md += f"- **Physical Release:** {movie.get('physicalRelease')}\n"
            md += "\n"
            
            # Genres and Keywords
            genres = movie.get('genres', [])
            if genres:
                md += f"**Genres:** {', '.join(genres)}\n\n"
            
            keywords = movie.get('keywords', [])
            if keywords:
                md += f"**Keywords:** {', '.join(keywords[:10])}\n\n"
            
            # Radarr Configuration
            md += "## ⚙️ Radarr Configuration\n\n"
            md += f"- **Monitored:** {'✅ Yes' if movie.get('monitored') else '❌ No'}\n"
            md += f"- **Quality Profile ID:** {movie.get('qualityProfileId', 'N/A')}\n"
            md += f"- **Minimum Availability:** {movie.get('minimumAvailability', 'N/A')}\n"
            md += f"- **Path:** `{movie.get('path', 'N/A')}`\n"
            md += f"- **Root Folder:** `{movie.get('rootFolderPath', 'N/A')}`\n\n"
            
            # File Details (if available)
            md += "## 💾 File Status\n\n"
            if movie.get('hasFile'):
                md += "**Status:** ✅ Downloaded\n\n"
                
                movie_file = movie.get('movieFile', {})
                if movie_file:
                    md += "### File Details\n\n"
                    md += f"- **File ID:** {movie_file.get('id', 'N/A')}\n"
                    md += f"- **Relative Path:** `{movie_file.get('relativePath', 'N/A')}`\n"
                    
                    # Quality information
                    quality_info = movie_file.get('quality', {}).get('quality', {})
                    md += f"- **Quality:** {quality_info.get('name', 'Unknown')}\n"
                    
                    # File size
                    size_bytes = movie_file.get('size', 0)
                    size_gb = round(size_bytes / (1024**3), 2) if size_bytes > 0 else 0
                    size_mb = round(size_bytes / (1024**2), 2) if size_bytes > 0 else 0
                    md += f"- **Size:** {size_gb} GB ({size_mb} MB)\n"
                    
                    # Media info
                    media_info = movie_file.get('mediaInfo', {})
                    if media_info:
                        md += f"- **Video Codec:** {media_info.get('videoCodec', 'N/A')}\n"
                        md += f"- **Audio Codec:** {media_info.get('audioCodec', 'N/A')}\n"
                        md += f"- **Resolution:** {media_info.get('resolution', 'N/A')}\n"
                        md += f"- **Runtime:** {media_info.get('runTime', 'N/A')}\n"
                    
                    md += f"- **Date Added:** {movie_file.get('dateAdded', 'N/A')}\n"
            else:
                md += "**Status:** ❌ Not Downloaded\n\n"
                md += f"- **Size on Disk:** {movie.get('sizeOnDisk', 0)} bytes\n"
                md += f"- **Available:** {'Yes' if movie.get('isAvailable') else 'No'}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrSearchTool(RequestsTool):
    """Custom tool for Radarr movie search results with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr search results to Markdown table."""
        try:
            items = json.loads(output)
            if not isinstance(items, list):
                return output
            
            if not items:
                return "# 🔍 Radarr Movie Search\n\n*No results found.*"
            
            md = f"# 🔍 Radarr Movie Search Results\n\n**Found {len(items)} results**\n\n"
            md += "| # | Title | Year | Status | Studio | In Library | TMDB | IMDB | Genres | Overview |\n"
            md += "|---:|:---|:---:|:---|:---|:---:|:---:|:---:|:---|:---|\n"
            
            for idx, item in enumerate(items, 1):
                title = item.get('title', 'Unknown')
                year = item.get('year', 'N/A')
                status = item.get('status', 'Unknown')
                studio = item.get('studio', 'Unknown')
                
                # Already in library?
                in_library = '✅' if item.get('hasFile') or item.get('id', 0) > 0 else '❌'
                
                tmdb_id = item.get('tmdbId', 'N/A')
                imdb_id = item.get('imdbId', 'N/A')
                
                # Genres
                genres = item.get('genres', [])
                genres_str = ', '.join(genres[:3]) if genres else '-'
                if len(genres) > 3:
                    genres_str += '...'
                
                # Overview (truncated)
                overview = item.get('overview', '')
                if overview:
                    overview = overview[:100] + '...' if len(overview) > 100 else overview
                    # Escape pipe characters
                    overview = overview.replace('|', '\\|')
                else:
                    overview = '-'
                
                md += f"| {idx} "
                md += f"| {title} "
                md += f"| {year} "
                md += f"| {status} "
                md += f"| {studio} "
                md += f"| {in_library} "
                md += f"| {tmdb_id} "
                md += f"| {imdb_id} "
                md += f"| {genres_str} "
                md += f"| {overview} |\n"
            
            md += f"\n---\n\n**Total Results:** {len(items)}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrQueueTool(RequestsTool):
    """Custom tool for Radarr download queue with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr queue output to Markdown table."""
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return output
            
            records = data.get('records', [])
            if not records:
                return "# 📥 Radarr Download Queue\n\n*Queue is empty.*"
            
            md = "# 📥 Radarr Download Queue\n\n"
            md += "| ID | Movie | Status | Progress | Quality | Size | ETA | Protocol |\n"
            md += "|---:|:---|:---|---:|:---|---:|:---|:---|\n"
            
            for item in records:
                item_id = item.get('id', 'N/A')
                
                # Get movie title
                movie = item.get('movie', {})
                title = movie.get('title', item.get('title', 'Unknown'))
                
                status = item.get('status', 'Unknown')
                
                # Calculate progress
                size_bytes = item.get('size', 0)
                sizeleft = item.get('sizeleft', 0)
                progress = 0
                if size_bytes > 0:
                    progress = round((1 - sizeleft / size_bytes) * 100, 1)
                
                # Quality
                quality = item.get('quality', {}).get('quality', {}).get('name', 'Unknown')
                
                # Size
                size_gb = round(size_bytes / (1024**3), 2) if size_bytes > 0 else 0
                
                # ETA
                eta = item.get('estimatedCompletionTime', 'N/A')
                if eta != 'N/A' and 'T' in str(eta):
                    eta = eta.split('T')[1][:5] if 'T' in eta else eta
                
                # Protocol
                protocol = item.get('protocol', 'Unknown')
                
                md += f"| {item_id} "
                md += f"| {title} "
                md += f"| {status} "
                md += f"| {progress}% "
                md += f"| {quality} "
                md += f"| {size_gb} GB "
                md += f"| {eta} "
                md += f"| {protocol} |\n"
            
            total = data.get('totalRecords', len(records))
            md += f"\n---\n\n**Total Items:** {total}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


class RadarrCalendarTool(RequestsTool):
    """Custom tool for Radarr calendar with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr calendar output to Markdown table."""
        try:
            items = json.loads(output)
            if not isinstance(items, list):
                return output
            
            if not items:
                return "# 📅 Radarr Upcoming Releases\n\n*No upcoming releases found.*"
            
            md = "# 📅 Radarr Upcoming Movie Releases\n\n"
            md += "| Title | Year | Release Type | Release Date | Status | Monitored | Downloaded |\n"
            md += "|:---|:---:|:---|:---|:---|:---:|:---:|\n"
            
            for item in items:
                title = item.get('title', 'Unknown')
                year = item.get('year', 'N/A')
                
                # Determine release type and date from MovieResource
                release_type = 'Unknown'
                release_date = 'N/A'
                
                if item.get('inCinemas'):
                    release_type = '🎭 Cinema'
                    release_date = item.get('inCinemas', 'N/A')
                elif item.get('digitalRelease'):
                    release_type = '💻 Digital'
                    release_date = item.get('digitalRelease', 'N/A')
                elif item.get('physicalRelease'):
                    release_type = '📀 Physical'
                    release_date = item.get('physicalRelease', 'N/A')
                
                status = item.get('status', 'Unknown')
                monitored = '✅' if item.get('monitored') else '❌'
                downloaded = '✅' if item.get('hasFile') else '❌'
                
                md += f"| {title} "
                md += f"| {year} "
                md += f"| {release_type} "
                md += f"| {release_date} "
                md += f"| {status} "
                md += f"| {monitored} "
                md += f"| {downloaded} |\n"
            
            md += f"\n---\n\n**Total Releases:** {len(items)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrHistoryTool(RequestsTool):
    """Custom tool for Radarr history with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr history to Markdown table."""
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return output
            
            records = data.get('records', [])
            if not records:
                return "# 📜 Radarr History\n\n*No history records found.*"
            
            md = "# 📜 Radarr History\n\n"
            md += "| Date | Event | Movie | Quality | Source | Release |\n"
            md += "|:---|:---|:---|:---|:---|:---|\n"
            
            for record in records:
                date = record.get('date', 'N/A')
                if 'T' in str(date):
                    date = date.split('T')[0]
                
                event_type = record.get('eventType', 'Unknown')
                
                # Get movie title
                movie = record.get('movie', {})
                title = movie.get('title', 'Unknown')
                
                # Quality
                quality = record.get('quality', {}).get('quality', {}).get('name', 'N/A')
                
                # Source
                source_title = record.get('sourceTitle', 'N/A')
                if len(source_title) > 40:
                    source_title = source_title[:40] + '...'
                
                # Download ID or indexer
                indexer = record.get('data', {}).get('indexer', 'N/A')
                
                md += f"| {date} "
                md += f"| {event_type} "
                md += f"| {title} "
                md += f"| {quality} "
                md += f"| {indexer} "
                md += f"| {source_title} |\n"
            
            total = data.get('totalRecords', len(records))
            page = data.get('page', 1)
            md += f"\n---\n\n**Page:** {page} | **Total Records:** {total}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrSystemStatusTool(RequestsTool):
    """Custom tool for Radarr system status with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr system status to Markdown."""
        try:
            status = json.loads(output)
            if not isinstance(status, dict):
                return output
            
            app_name = status.get('appName', 'Radarr')
            md = f"# 🎬 {app_name} System Status\n\n"
            
            md += "## 📌 Version Information\n\n"
            md += f"- **Version:** {status.get('version', 'N/A')}\n"
            md += f"- **Branch:** {status.get('branch', 'N/A')}\n"
            md += f"- **Build Time:** {status.get('buildTime', 'N/A')}\n"
            md += f"- **Database:** {status.get('databaseType', 'N/A')} (v{status.get('databaseVersion', 'N/A')})\n"
            md += f"- **Runtime:** {status.get('runtimeName', 'N/A')} {status.get('runtimeVersion', 'N/A')}\n\n"
            
            md += "## 💻 Platform\n\n"
            md += f"- **OS:** {status.get('osName', 'Unknown')} {status.get('osVersion', '')}\n"
            md += f"- **Is Linux:** {'Yes' if status.get('isLinux') else 'No'}\n"
            md += f"- **Is macOS:** {'Yes' if status.get('isOsx') else 'No'}\n"
            md += f"- **Is Windows:** {'Yes' if status.get('isWindows') else 'No'}\n"
            md += f"- **Is Docker:** {'Yes' if status.get('isDocker') else 'No'}\n"
            md += f"- **Mode:** {status.get('mode', 'Unknown')}\n\n"
            
            md += "## ⚙️ Configuration\n\n"
            md += f"- **Start Time:** {status.get('startTime', 'N/A')}\n"
            md += f"- **URL Base:** `{status.get('urlBase', '/')}`\n"
            md += f"- **Authentication:** {status.get('authentication', 'Unknown')}\n"
            md += f"- **Instance Name:** {status.get('instanceName', 'N/A')}\n"
            md += f"- **Migration Version:** {status.get('migrationVersion', 'N/A')}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrQualityProfilesTool(RequestsTool):
    """Custom tool for Radarr quality profiles with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr quality profiles to Markdown table."""
        try:
            profiles = json.loads(output)
            if not isinstance(profiles, list):
                return output
            
            if not profiles:
                return "# 🎯 Radarr Quality Profiles\n\n*No quality profiles configured.*"
            
            md = "# 🎯 Radarr Quality Profiles\n\n"
            md += "| ID | Name | Upgrade Allowed | Cutoff | Min Format Score | Language |\n"
            md += "|---:|:---|:---:|:---|---:|:---|\n"
            
            for profile in profiles:
                profile_id = profile.get('id', 'N/A')
                name = profile.get('name', 'Unknown')
                upgrade_allowed = '✅' if profile.get('upgradeAllowed') else '❌'
                cutoff = profile.get('cutoff', 'N/A')
                min_format_score = profile.get('minFormatScore', 0)
                language = profile.get('language', {}).get('name', 'N/A')
                
                md += f"| {profile_id} "
                md += f"| {name} "
                md += f"| {upgrade_allowed} "
                md += f"| {cutoff} "
                md += f"| {min_format_score} "
                md += f"| {language} |\n"
            
            md += f"\n---\n\n**Total Profiles:** {len(profiles)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrRootFoldersTool(RequestsTool):
    """Custom tool for Radarr root folders with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr root folders to Markdown table."""
        try:
            folders = json.loads(output)
            if not isinstance(folders, list):
                return output
            
            if not folders:
                return "# 📁 Radarr Root Folders\n\n*No root folders configured.*"
            
            md = "# 📁 Radarr Root Folders\n\n"
            md += "| ID | Path | Free Space | Total Space | Accessible | Unmapped Folders |\n"
            md += "|---:|:---|---:|---:|:---:|---:|\n"
            
            for folder in folders:
                folder_id = folder.get('id', 'N/A')
                path = folder.get('path', 'Unknown')
                
                free_bytes = folder.get('freeSpace', 0)
                total_bytes = folder.get('totalSpace', 0)
                free_gb = round(free_bytes / (1024**3), 2)
                total_gb = round(total_bytes / (1024**3), 2)
                
                accessible = '✅' if folder.get('accessible', True) else '❌'
                
                unmapped_folders = folder.get('unmappedFolders', [])
                unmapped_count = len(unmapped_folders) if unmapped_folders else 0
                
                md += f"| {folder_id} "
                md += f"| `{path}` "
                md += f"| {free_gb} GB "
                md += f"| {total_gb} GB "
                md += f"| {accessible} "
                md += f"| {unmapped_count} |\n"
            
            md += f"\n---\n\n**Total Folders:** {len(folders)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class RadarrDiskSpaceTool(RequestsTool):
    """Custom tool for Radarr disk space with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Radarr disk space data to Markdown table."""
        try:
            spaces = json.loads(output)
            if not isinstance(spaces, list):
                return output
            
            if not spaces:
                return "# 💿 Radarr Disk Space\n\n*No disk space information available.*"
            
            md = "# 💿 Radarr Disk Space\n\n"
            md += "| Path | Label | Free Space | Total Space | % Free |\n"
            md += "|:---|:---|---:|---:|---:|\n"
            
            for space in spaces:
                path = space.get('path', 'Unknown')
                label = space.get('label', 'N/A')
                
                free_bytes = space.get('freeSpace', 0)
                total_bytes = space.get('totalSpace', 0)
                
                free_gb = round(free_bytes / (1024**3), 2)
                total_gb = round(total_bytes / (1024**3), 2)
                
                percent_free = round((free_bytes / total_bytes * 100), 1) if total_bytes > 0 else 0
                
                md += f"| `{path}` "
                md += f"| {label} "
                md += f"| {free_gb} GB "
                md += f"| {total_gb} GB "
                md += f"| {percent_free}% |\n"
            
            total_free = sum(s.get('freeSpace', 0) for s in spaces)
            total_space = sum(s.get('totalSpace', 0) for s in spaces)
            md += f"\n---\n\n**Total Free:** {round(total_free / (1024**3), 2)} GB | **Total Space:** {round(total_space / (1024**3), 2)} GB\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


# =============================================================================
# SONARR CUSTOM TOOL CLASSES WITH OUTPUT POST-PROCESSING  
# =============================================================================

class SonarrSeriesListTool(RequestsTool):
    """Custom tool for listing Sonarr series with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert series list output to Markdown table based on SeriesResource schema."""
        try:
            series_list = json.loads(output)
            if not isinstance(series_list, list):
                return output
            
            if not series_list:
                return "# 📺 Sonarr Series Library\n\n*No series found in library.*"
            
            # Build Markdown table
            md = "# 📺 Sonarr Series Library\n\n"
            md += "| ID | Title | Year | Status | Network | Monitored | Seasons | Episodes | Downloaded | % Complete | Next Airing |\n"
            md += "|---:|:---|:---:|:---|:---|:---:|---:|---:|---:|---:|:---|\n"
            
            for series in series_list:
                series_id = series.get('id', 'N/A')
                title = series.get('title', 'Unknown')
                year = series.get('year', 'N/A')
                status = series.get('status', 'Unknown')
                network = series.get('network', 'Unknown')
                monitored = '✅' if series.get('monitored') else '❌'
                
                # Statistics from SeriesResource
                stats = series.get("statistics", {})
                season_count = series.get('seasonCount', 0)
                episode_count = stats.get('episodeCount', 0)
                episode_file_count = stats.get('episodeFileCount', 0)
                percent = round(stats.get('percentOfEpisodes', 0), 1)
                
                next_airing = series.get('nextAiring', 'N/A')
                if next_airing != 'N/A' and 'T' in str(next_airing):
                    next_airing = next_airing.split('T')[0]
                
                md += f"| {series_id} "
                md += f"| {title} "
                md += f"| {year} "
                md += f"| {status} "
                md += f"| {network} "
                md += f"| {monitored} "
                md += f"| {season_count} "
                md += f"| {episode_count} "
                md += f"| {episode_file_count} "
                md += f"| {percent}% "
                md += f"| {next_airing} |\n"
            
            total_episodes = sum(s.get('statistics', {}).get('episodeCount', 0) for s in series_list)
            total_downloaded = sum(s.get('statistics', {}).get('episodeFileCount', 0) for s in series_list)
            
            md += f"\n---\n\n"
            md += f"**📊 Summary:** {len(series_list)} series • {total_episodes} episodes • {total_downloaded} downloaded ({round(total_downloaded/total_episodes*100 if total_episodes > 0 else 0, 1)}%)\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


class SonarrSeriesDetailTool(RequestsTool):
    """Custom tool for getting Sonarr series details with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert series detail output to formatted Markdown based on SeriesResource schema."""
        try:
            series = json.loads(output)
            if not isinstance(series, dict):
                return output
            
            # Build comprehensive Markdown output
            title = series.get('title', 'Unknown Series')
            year = series.get('year', 'N/A')
            md = f"# 📺 {title} ({year})\n\n"
            
            # Overview section
            md += "## 📋 Overview\n\n"
            overview = series.get('overview', 'No overview available.')
            md += f"{overview}\n\n"
            
            # Basic Information from SeriesResource
            md += "## ℹ️ Information\n\n"
            md += f"- **Sonarr ID:** {series.get('id', 'N/A')}\n"
            md += f"- **Status:** {series.get('status', 'Unknown')}\n"
            md += f"- **Network:** {series.get('network', 'Unknown')}\n"
            md += f"- **Air Time:** {series.get('airTime', 'Unknown')}\n"
            md += f"- **Series Type:** {series.get('seriesType', 'Standard')}\n"
            md += f"- **Runtime:** {series.get('runtime', 0)} minutes\n"
            md += f"- **Certification:** {series.get('certification', 'Not Rated')}\n"
            md += f"- **Ended:** {'Yes' if series.get('ended') else 'No'}\n\n"
            
            # External IDs from SeriesResource
            md += "## 🔗 External IDs\n\n"
            md += f"- **TVDB ID:** {series.get('tvdbId', 'N/A')}\n"
            md += f"- **TMDB ID:** {series.get('tmdbId', 'N/A')}\n"
            md += f"- **IMDB ID:** {series.get('imdbId', 'N/A')}\n"
            md += f"- **TVRage ID:** {series.get('tvRageId', 'N/A')}\n"
            md += f"- **TVMaze ID:** {series.get('tvMazeId', 'N/A')}\n\n"
            
            # Airing Information
            md += "## 📅 Airing Information\n\n"
            if series.get('firstAired'):
                md += f"- **First Aired:** {series.get('firstAired')}\n"
            if series.get('lastAired'):
                md += f"- **Last Aired:** {series.get('lastAired')}\n"
            if series.get('previousAiring'):
                md += f"- **Previous Airing:** {series.get('previousAiring')}\n"
            if series.get('nextAiring'):
                md += f"- **Next Airing:** {series.get('nextAiring')}\n"
            md += "\n"
            
            # Genres
            genres = series.get('genres', [])
            if genres:
                md += f"**Genres:** {', '.join(genres)}\n\n"
            
            # Sonarr Configuration
            md += "## ⚙️ Sonarr Configuration\n\n"
            md += f"- **Monitored:** {'✅ Yes' if series.get('monitored') else '❌ No'}\n"
            md += f"- **Monitor New Items:** {series.get('monitorNewItems', 'N/A')}\n"
            md += f"- **Quality Profile ID:** {series.get('qualityProfileId', 'N/A')}\n"
            md += f"- **Season Folder:** {'Yes' if series.get('seasonFolder') else 'No'}\n"
            md += f"- **Use Scene Numbering:** {'Yes' if series.get('useSceneNumbering') else 'No'}\n"
            md += f"- **Path:** `{series.get('path', 'N/A')}`\n"
            md += f"- **Root Folder:** `{series.get('rootFolderPath', 'N/A')}`\n\n"
            
            # Overall Statistics
            stats = series.get("statistics", {})
            md += "## 📊 Statistics\n\n"
            md += f"- **Total Seasons:** {series.get('seasonCount', 0)}\n"
            md += f"- **Total Episodes:** {stats.get('episodeCount', 0)}\n"
            md += f"- **Downloaded Episodes:** {stats.get('episodeFileCount', 0)}\n"
            md += f"- **Completion:** {round(stats.get('percentOfEpisodes', 0), 1)}%\n"
            md += f"- **Total File Size:** {round(stats.get('sizeOnDisk', 0) / (1024**3), 2)} GB\n\n"
            
            # Seasons Table
            seasons = series.get("seasons", [])
            if seasons:
                md += "## 📑 Seasons Breakdown\n\n"
                md += "| Season | Monitored | Episodes | Downloaded | % Complete | Size on Disk |\n"
                md += "|---:|:---:|---:|---:|---:|---:|\n"
                
                for season in seasons:
                    season_stats = season.get("statistics", {})
                    season_num = season.get("seasonNumber", 0)
                    monitored = '✅' if season.get('monitored') else '❌'
                    episodes = season_stats.get('episodeCount', 0)
                    downloaded = season_stats.get('episodeFileCount', 0)
                    percent = round(season_stats.get('percentOfEpisodes', 0), 1)
                    size_gb = round(season_stats.get('sizeOnDisk', 0) / (1024**3), 2)
                    
                    md += f"| {season_num} "
                    md += f"| {monitored} "
                    md += f"| {episodes} "
                    md += f"| {downloaded} "
                    md += f"| {percent}% "
                    md += f"| {size_gb} GB |\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrEpisodeListTool(RequestsTool):
    """Custom tool for listing Sonarr episodes with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert episode list to Markdown table based on EpisodeResource schema."""
        try:
            episodes = json.loads(output)
            if not isinstance(episodes, list):
                return output
            
            if not episodes:
                return "# 📺 Episodes\n\n*No episodes found.*"
            
            # Build Markdown table
            md = "# 📺 Episodes\n\n"
            md += "| ID | Episode | Title | Air Date | Runtime | Monitored | Downloaded | File ID |\n"
            md += "|---:|:---:|:---|:---|---:|:---:|:---:|---:|\n"
            
            for ep in episodes:
                ep_id = ep.get('id', 'N/A')
                season = ep.get('seasonNumber', 0)
                episode = ep.get('episodeNumber', 0)
                ep_code = f"S{season:02d}E{episode:02d}"
                
                title = ep.get('title', 'Unknown')
                air_date = ep.get('airDate', 'N/A')
                runtime = ep.get('runtime', 0)
                monitored = '✅' if ep.get('monitored') else '❌'
                has_file = '✅' if ep.get('hasFile') else '❌'
                file_id = ep.get('episodeFileId', '-')
                
                md += f"| {ep_id} "
                md += f"| {ep_code} "
                md += f"| {title} "
                md += f"| {air_date} "
                md += f"| {runtime} min "
                md += f"| {monitored} "
                md += f"| {has_file} "
                md += f"| {file_id} |\n"
            
            downloaded = sum(1 for ep in episodes if ep.get('hasFile'))
            monitored_count = sum(1 for ep in episodes if ep.get('monitored'))
            
            md += f"\n---\n\n"
            md += f"**Total:** {len(episodes)} episodes • **Downloaded:** {downloaded} ({round(downloaded/len(episodes)*100, 1)}%) • **Monitored:** {monitored_count}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


class SonarrSearchTool(RequestsTool):
    """Custom tool for Sonarr series search results with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr search results to Markdown table."""
        try:
            items = json.loads(output)
            if not isinstance(items, list):
                return output
            
            if not items:
                return "# 🔍 Sonarr Series Search\n\n*No results found.*"
            
            md = f"# 🔍 Sonarr Series Search Results\n\n**Found {len(items)} results**\n\n"
            md += "| # | Title | Year | Status | Network | Type | Seasons | Episodes | In Library | TVDB | IMDB | Genres | Overview |\n"
            md += "|---:|:---|:---:|:---|:---|:---|---:|---:|:---:|:---:|:---:|:---|:---|\n"
            
            for idx, item in enumerate(items, 1):
                title = item.get('title', 'Unknown')
                year = item.get('year', 'N/A')
                status = item.get('status', 'Unknown')
                network = item.get('network', 'Unknown')
                series_type = item.get('seriesType', 'Standard')
                
                # Statistics
                stats = item.get('statistics', {})
                season_count = item.get('seasonCount', 0)
                episode_count = stats.get('episodeCount', 0)
                
                # Already in library?
                in_library = '✅' if stats.get('episodeFileCount', 0) > 0 or item.get('id', 0) > 0 else '❌'
                
                # IDs
                tvdb_id = item.get('tvdbId', 'N/A')
                imdb_id = item.get('imdbId', 'N/A')
                
                # Genres
                genres = item.get('genres', [])
                genres_str = ', '.join(genres[:3]) if genres else '-'
                if len(genres) > 3:
                    genres_str += '...'
                
                # Overview (truncated)
                overview = item.get('overview', '')
                if overview:
                    overview = overview[:100] + '...' if len(overview) > 100 else overview
                    # Escape pipe characters
                    overview = overview.replace('|', '\\|')
                else:
                    overview = '-'
                
                md += f"| {idx} "
                md += f"| {title} "
                md += f"| {year} "
                md += f"| {status} "
                md += f"| {network} "
                md += f"| {series_type} "
                md += f"| {season_count} "
                md += f"| {episode_count} "
                md += f"| {in_library} "
                md += f"| {tvdb_id} "
                md += f"| {imdb_id} "
                md += f"| {genres_str} "
                md += f"| {overview} |\n"
            
            md += f"\n---\n\n**Total Results:** {len(items)}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrQueueTool(RequestsTool):
    """Custom tool for Sonarr download queue with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr queue output to Markdown table."""
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return output
            
            records = data.get('records', [])
            if not records:
                return "# 📥 Sonarr Download Queue\n\n*Queue is empty.*"
            
            md = "# 📥 Sonarr Download Queue\n\n"
            md += "| ID | Series | Episode | Status | Progress | Quality | Size | ETA | Protocol |\n"
            md += "|---:|:---|:---|:---|---:|:---|---:|:---|:---|\n"
            
            for item in records:
                item_id = item.get('id', 'N/A')
                
                # Get series and episode info
                series = item.get('series', {})
                episode = item.get('episode', {})
                
                series_title = series.get('title', 'Unknown')
                season = episode.get('seasonNumber', 0)
                ep_num = episode.get('episodeNumber', 0)
                episode_str = f"S{season:02d}E{ep_num:02d}"
                
                status = item.get('status', 'Unknown')
                
                # Calculate progress
                size_bytes = item.get('size', 0)
                sizeleft = item.get('sizeleft', 0)
                progress = 0
                if size_bytes > 0:
                    progress = round((1 - sizeleft / size_bytes) * 100, 1)
                
                # Quality
                quality = item.get('quality', {}).get('quality', {}).get('name', 'Unknown')
                
                # Size
                size_gb = round(size_bytes / (1024**3), 2) if size_bytes > 0 else 0
                
                # ETA
                eta = item.get('estimatedCompletionTime', 'N/A')
                if eta != 'N/A' and 'T' in str(eta):
                    eta = eta.split('T')[1][:5] if 'T' in eta else eta
                
                # Protocol
                protocol = item.get('protocol', 'Unknown')
                
                md += f"| {item_id} "
                md += f"| {series_title} "
                md += f"| {episode_str} "
                md += f"| {status} "
                md += f"| {progress}% "
                md += f"| {quality} "
                md += f"| {size_gb} GB "
                md += f"| {eta} "
                md += f"| {protocol} |\n"
            
            total = data.get('totalRecords', len(records))
            md += f"\n---\n\n**Total Items:** {total}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output


class SonarrCalendarTool(RequestsTool):
    """Custom tool for Sonarr calendar with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr calendar output to Markdown table."""
        try:
            items = json.loads(output)
            if not isinstance(items, list):
                return output
            
            if not items:
                return "# 📅 Sonarr Upcoming Episodes\n\n*No upcoming episodes found.*"
            
            md = "# 📅 Sonarr Upcoming Episodes\n\n"
            md += "| Series | Episode | Title | Air Date | Runtime | Monitored | Downloaded |\n"
            md += "|:---|:---:|:---|:---|---:|:---:|:---:|\n"
            
            for item in items:
                # Get series info
                series = item.get('series', {})
                series_title = series.get('title', item.get('seriesTitle', 'Unknown'))
                
                # Episode info from EpisodeResource
                season = item.get('seasonNumber', 0)
                episode = item.get('episodeNumber', 0)
                ep_code = f"S{season:02d}E{episode:02d}"
                
                title = item.get('title', 'Unknown')
                air_date = item.get('airDate', 'N/A')
                runtime = item.get('runtime', 0)
                monitored = '✅' if item.get('monitored') else '❌'
                has_file = '✅' if item.get('hasFile') else '❌'
                
                md += f"| {series_title} "
                md += f"| {ep_code} "
                md += f"| {title} "
                md += f"| {air_date} "
                md += f"| {runtime} min "
                md += f"| {monitored} "
                md += f"| {has_file} |\n"
            
            md += f"\n---\n\n**Total Episodes:** {len(items)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrHistoryTool(RequestsTool):
    """Custom tool for Sonarr history with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr history to Markdown table."""
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return output
            
            records = data.get('records', [])
            if not records:
                return "# 📜 Sonarr History\n\n*No history records found.*"
            
            md = "# 📜 Sonarr History\n\n"
            md += "| Date | Event | Series | Episode | Quality | Source | Release |\n"
            md += "|:---|:---|:---|:---:|:---|:---|:---|\n"
            
            for record in records:
                date = record.get('date', 'N/A')
                if 'T' in str(date):
                    date = date.split('T')[0]
                
                event_type = record.get('eventType', 'Unknown')
                
                # Get series and episode
                series = record.get('series', {})
                episode = record.get('episode', {})
                
                series_title = series.get('title', 'Unknown')
                season = episode.get('seasonNumber', 0)
                ep_num = episode.get('episodeNumber', 0)
                ep_code = f"S{season:02d}E{ep_num:02d}" if season or ep_num else 'N/A'
                
                # Quality
                quality = record.get('quality', {}).get('quality', {}).get('name', 'N/A')
                
                # Source
                source_title = record.get('sourceTitle', 'N/A')
                if len(source_title) > 40:
                    source_title = source_title[:40] + '...'
                
                # Download ID or indexer
                indexer = record.get('data', {}).get('indexer', 'N/A')
                
                md += f"| {date} "
                md += f"| {event_type} "
                md += f"| {series_title} "
                md += f"| {ep_code} "
                md += f"| {quality} "
                md += f"| {indexer} "
                md += f"| {source_title} |\n"
            
            total = data.get('totalRecords', len(records))
            page = data.get('page', 1)
            md += f"\n---\n\n**Page:** {page} | **Total Records:** {total}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrWantedTool(RequestsTool):
    """Custom tool for Sonarr wanted/missing episodes with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr wanted items to Markdown table."""
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return output
            
            records = data.get('records', [])
            if not records:
                return "# ⚠️ Sonarr Missing Episodes\n\n*No missing episodes found.*"
            
            md = "# ⚠️ Sonarr Missing Episodes\n\n"
            md += "| Series | Episode | Title | Air Date | Monitored | Last Searched |\n"
            md += "|:---|:---:|:---|:---|:---:|:---|\n"
            
            for item in records:
                # Get series info
                series = item.get('series', {})
                series_title = series.get('title', 'Unknown')
                
                # Episode info from EpisodeResource
                season = item.get('seasonNumber', 0)
                episode = item.get('episodeNumber', 0)
                ep_code = f"S{season:02d}E{episode:02d}"
                
                title = item.get('title', 'Unknown')
                air_date = item.get('airDate', 'N/A')
                monitored = '✅' if item.get('monitored') else '❌'
                
                last_search = item.get('lastSearchTime', 'Never')
                if last_search != 'Never' and 'T' in str(last_search):
                    last_search = last_search.split('T')[0]
                
                md += f"| {series_title} "
                md += f"| {ep_code} "
                md += f"| {title} "
                md += f"| {air_date} "
                md += f"| {monitored} "
                md += f"| {last_search} |\n"
            
            total = data.get('totalRecords', len(records))
            page = data.get('page', 1)
            md += f"\n---\n\n**Page:** {page} | **Total Missing:** {total}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrSystemStatusTool(RequestsTool):
    """Custom tool for Sonarr system status with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr system status to Markdown."""
        try:
            status = json.loads(output)
            if not isinstance(status, dict):
                return output
            
            app_name = status.get('appName', 'Sonarr')
            md = f"# 📺 {app_name} System Status\n\n"
            
            md += "## 📌 Version Information\n\n"
            md += f"- **Version:** {status.get('version', 'N/A')}\n"
            md += f"- **Branch:** {status.get('branch', 'N/A')}\n"
            md += f"- **Build Time:** {status.get('buildTime', 'N/A')}\n"
            md += f"- **Database:** {status.get('databaseType', 'N/A')} (v{status.get('databaseVersion', 'N/A')})\n"
            md += f"- **Runtime:** {status.get('runtimeName', 'N/A')} {status.get('runtimeVersion', 'N/A')}\n\n"
            
            md += "## 💻 Platform\n\n"
            md += f"- **OS:** {status.get('osName', 'Unknown')} {status.get('osVersion', '')}\n"
            md += f"- **Is Linux:** {'Yes' if status.get('isLinux') else 'No'}\n"
            md += f"- **Is macOS:** {'Yes' if status.get('isOsx') else 'No'}\n"
            md += f"- **Is Windows:** {'Yes' if status.get('isWindows') else 'No'}\n"
            md += f"- **Is Docker:** {'Yes' if status.get('isDocker') else 'No'}\n"
            md += f"- **Mode:** {status.get('mode', 'Unknown')}\n\n"
            
            md += "## ⚙️ Configuration\n\n"
            md += f"- **Start Time:** {status.get('startTime', 'N/A')}\n"
            md += f"- **URL Base:** `{status.get('urlBase', '/')}`\n"
            md += f"- **Authentication:** {status.get('authentication', 'Unknown')}\n"
            md += f"- **Instance Name:** {status.get('instanceName', 'N/A')}\n"
            md += f"- **Migration Version:** {status.get('migrationVersion', 'N/A')}\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrQualityProfilesTool(RequestsTool):
    """Custom tool for Sonarr quality profiles with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr quality profiles to Markdown table."""
        try:
            profiles = json.loads(output)
            if not isinstance(profiles, list):
                return output
            
            if not profiles:
                return "# 🎯 Sonarr Quality Profiles\n\n*No quality profiles configured.*"
            
            md = "# 🎯 Sonarr Quality Profiles\n\n"
            md += "| ID | Name | Upgrade Allowed | Cutoff | Min Format Score | Language |\n"
            md += "|---:|:---|:---:|:---|---:|:---|\n"
            
            for profile in profiles:
                profile_id = profile.get('id', 'N/A')
                name = profile.get('name', 'Unknown')
                upgrade_allowed = '✅' if profile.get('upgradeAllowed') else '❌'
                cutoff = profile.get('cutoff', 'N/A')
                min_format_score = profile.get('minFormatScore', 0)
                language = profile.get('language', {}).get('name', 'N/A')
                
                md += f"| {profile_id} "
                md += f"| {name} "
                md += f"| {upgrade_allowed} "
                md += f"| {cutoff} "
                md += f"| {min_format_score} "
                md += f"| {language} |\n"
            
            md += f"\n---\n\n**Total Profiles:** {len(profiles)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrRootFoldersTool(RequestsTool):
    """Custom tool for Sonarr root folders with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr root folders to Markdown table."""
        try:
            folders = json.loads(output)
            if not isinstance(folders, list):
                return output
            
            if not folders:
                return "# 📁 Sonarr Root Folders\n\n*No root folders configured.*"
            
            md = "# 📁 Sonarr Root Folders\n\n"
            md += "| ID | Path | Free Space | Total Space | Accessible | Unmapped Folders |\n"
            md += "|---:|:---|---:|---:|:---:|---:|\n"
            
            for folder in folders:
                folder_id = folder.get('id', 'N/A')
                path = folder.get('path', 'Unknown')
                
                free_bytes = folder.get('freeSpace', 0)
                total_bytes = folder.get('totalSpace', 0)
                free_gb = round(free_bytes / (1024**3), 2)
                total_gb = round(total_bytes / (1024**3), 2)
                
                accessible = '✅' if folder.get('accessible', True) else '❌'
                
                unmapped_folders = folder.get('unmappedFolders', [])
                unmapped_count = len(unmapped_folders) if unmapped_folders else 0
                
                md += f"| {folder_id} "
                md += f"| `{path}` "
                md += f"| {free_gb} GB "
                md += f"| {total_gb} GB "
                md += f"| {accessible} "
                md += f"| {unmapped_count} |\n"
            
            md += f"\n---\n\n**Total Folders:** {len(folders)}\n"
            return md
        except (json.JSONDecodeError, KeyError, TypeError):
            return output


class SonarrDiskSpaceTool(RequestsTool):
    """Custom tool for Sonarr disk space with Markdown output."""
    
    def process_output(self, output: str) -> str:
        """Convert Sonarr disk space data to Markdown table."""
        try:
            spaces = json.loads(output)
            if not isinstance(spaces, list):
                return output
            
            if not spaces:
                return "# 💿 Sonarr Disk Space\n\n*No disk space information available.*"
            
            md = "# 💿 Sonarr Disk Space\n\n"
            md += "| Path | Label | Free Space | Total Space | % Free |\n"
            md += "|:---|:---|---:|---:|---:|\n"
            
            for space in spaces:
                path = space.get('path', 'Unknown')
                label = space.get('label', 'N/A')
                
                free_bytes = space.get('freeSpace', 0)
                total_bytes = space.get('totalSpace', 0)
                
                free_gb = round(free_bytes / (1024**3), 2)
                total_gb = round(total_bytes / (1024**3), 2)
                
                percent_free = round((free_bytes / total_bytes * 100), 1) if total_bytes > 0 else 0
                
                md += f"| `{path}` "
                md += f"| {label} "
                md += f"| {free_gb} GB "
                md += f"| {total_gb} GB "
                md += f"| {percent_free}% |\n"
            
            total_free = sum(s.get('freeSpace', 0) for s in spaces)
            total_space = sum(s.get('totalSpace', 0) for s in spaces)
            md += f"\n---\n\n**Total Free:** {round(total_free / (1024**3), 2)} GB | **Total Space:** {round(total_space / (1024**3), 2)} GB\n"
            
            return md
        except (json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
            return output



# =============================================================================
# RADARR TOOLS
# =============================================================================

radarr_get_movies = RadarrMovieListTool(
    name="radarr_get_movies",
    description="Get all movies from Radarr library. Returns array of movies with: title, year, hasFile (download status), monitored status, quality profile, ratings, and file details. Use this to get library overview or check download counts. For detailed info on a specific movie, use radarr_get_movie_by_id instead.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/movie",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "tmdbId": {
            "type": "integer",
            "description": "Filter by TMDB ID"
        }
    }
)

radarr_get_movie_by_id = RadarrMovieDetailTool(
    name="radarr_get_movie_by_id",
    description="Get detailed information about a specific movie by its Radarr ID. Returns complete movie data including: title, year, hasFile (download status), movieFile (file details if downloaded), monitored status, quality profile, ratings, and overview. Essential for checking if a movie is downloaded.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/movie/{{id}}",
    headers={"X-Api-Key": RADARR_API_KEY}
)

radarr_add_movie = RequestsTool(
    name="radarr_add_movie",
    description="Add a new movie to Radarr. Requires TMDB ID, title, quality profile, and root folder path. Note: The full path will be {rootFolderPath}/{movieTitle}.",
    method="POST",
    url_template=f"{RADARR_URL}/api/v3/movie",
    headers={"X-Api-Key": RADARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Movie title"},
            "tmdbId": {"type": "integer", "description": "TMDB ID of the movie"},
            "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
            "rootFolderPath": {"type": "string", "description": "Root folder path"},
            "monitored": {"type": "boolean", "description": "Whether to monitor the movie"},
            "addOptions": {
                "type": "object",
                "properties": {
                    "searchForMovie": {"type": "boolean", "description": "Search for movie after adding"}
                }
            }
        },
        "required": ["title", "tmdbId", "qualityProfileId", "rootFolderPath"]
    }
)

radarr_update_movie = RequestsTool(
    name="radarr_update_movie",
    description="Update an existing movie in Radarr. Can update monitored status, quality profile, tags, etc.",
    method="PUT",
    url_template=f"{RADARR_URL}/api/v3/movie/{{id}}",
    headers={"X-Api-Key": RADARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "monitored": {"type": "boolean", "description": "Monitor status"},
            "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
            "minimumAvailability": {"type": "string", "description": "Minimum availability"},
            "tags": {"type": "array", "items": {"type": "integer"}, "description": "Tag IDs"}
        }
    }
)

radarr_delete_movie = RequestsTool(
    name="radarr_delete_movie",
    description="Delete a movie from Radarr by its ID",
    method="DELETE",
    url_template=f"{RADARR_URL}/api/v3/movie/{{id}}",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "deleteFiles": {
            "type": "boolean",
            "description": "Delete movie files from disk",
            "required": False
        },
        "addImportExclusion": {
            "type": "boolean",
            "description": "Add to import exclusion list",
            "required": False
        }
    }
)

radarr_search_movies = RadarrSearchTool(
    name="radarr_search_movies",
    description="Search for movies to add to Radarr using a search term. Returns detailed search results with TMDB/IMDB IDs, status, studio, genres, and indicates if movie is already in library.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/movie/lookup",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "term": {
            "type": "string",
            "description": "Search term (movie title or TMDB ID with 'tmdb:' prefix)",
            "required": True
        }
    }
)

radarr_get_queue = RadarrQueueTool(
    name="radarr_get_queue",
    description="Get the current download queue in Radarr with pagination support. Shows download progress, quality, size, ETA, and protocol for each item in queue.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/queue",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "includeUnknownMovieItems": {"type": "boolean", "description": "Include unknown movies"}
    }
)

radarr_delete_queue_item = RequestsTool(
    name="radarr_delete_queue_item",
    description="Remove an item from the download queue",
    method="DELETE",
    url_template=f"{RADARR_URL}/api/v3/queue/{{id}}",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "removeFromClient": {"type": "boolean", "description": "Remove from download client"},
        "blocklist": {"type": "boolean", "description": "Add to blocklist"}
    }
)

radarr_get_calendar = RadarrCalendarTool(
    name="radarr_get_calendar",
    description="Get upcoming movie releases in a date range. Returns movies with release dates (cinema, digital, physical), download status, and file information. REQUIRED: Use ISO format dates (YYYY-MM-DD) for start and end parameters. For 'this week' calculate the date range from current date. Use this to answer questions about upcoming movie releases.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/calendar",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "start": {"type": "string", "description": "Start date in ISO format (YYYY-MM-DD)"},
        "end": {"type": "string", "description": "End date in ISO format (YYYY-MM-DD)"},
        "unmonitored": {"type": "boolean", "description": "Include unmonitored movies"}
    }
)

radarr_get_system_status = RadarrSystemStatusTool(
    name="radarr_get_system_status",
    description="Get Radarr system status including version, startup time, platform information, database details, and configuration settings.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/system/status",
    headers={"X-Api-Key": RADARR_API_KEY}
)

radarr_get_quality_profiles = RadarrQualityProfilesTool(
    name="radarr_get_quality_profiles",
    description="Get all quality profiles configured in Radarr with upgrade settings, cutoff, minimum format score, and language preferences.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/qualityprofile",
    headers={"X-Api-Key": RADARR_API_KEY}
)

radarr_get_root_folders = RadarrRootFoldersTool(
    name="radarr_get_root_folders",
    description="Get all root folders configured in Radarr with free/total space, accessibility status, and unmapped folders count.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/rootfolder",
    headers={"X-Api-Key": RADARR_API_KEY}
)

radarr_trigger_search = RequestsTool(
    name="radarr_trigger_search",
    description="Trigger a search for a specific movie",
    method="POST",
    url_template=f"{RADARR_URL}/api/v3/command",
    headers={"X-Api-Key": RADARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Command name: 'MoviesSearch'"},
            "movieIds": {"type": "array", "items": {"type": "integer"}, "description": "Movie IDs to search for"}
        },
        "required": ["name", "movieIds"]
    }
)

radarr_get_history = RadarrHistoryTool(
    name="radarr_get_history",
    description="Get Radarr history with pagination and filtering. Shows date, event type, movie title, quality, source indexer, and release name for all historical actions.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/history",
    headers={"X-Api-Key": RADARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "sortKey": {"type": "string", "description": "Sort field"},
        "movieId": {"type": "integer", "description": "Filter by movie ID"}
    }
)

radarr_get_disk_space = RadarrDiskSpaceTool(
    name="radarr_get_disk_space",
    description="Get disk space information for all root folders. Shows free and total space with percentage free for each storage location.",
    method="GET",
    url_template=f"{RADARR_URL}/api/v3/diskspace",
    headers={"X-Api-Key": RADARR_API_KEY}
)

# =============================================================================
# SONARR TOOLS
# =============================================================================

sonarr_get_series = SonarrSeriesListTool(
    name="sonarr_get_series",
    description="Get all TV series from Sonarr library. Returns detailed statistics including: episodeCount (total episodes), episodeFileCount (downloaded episodes), seasons array with monitored status per season, percentOfEpisodes (download percentage), and series monitoring status. Use this to check download progress and monitored seasons.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/series",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "tvdbId": {"type": "integer", "description": "Filter by TVDB ID"},
        "includeSeasonImages": {"type": "boolean", "description": "Include season images"},
        "id": {"type": "integer", "description": "Filter by series ID"}
    }
)

sonarr_get_series_by_id = SonarrSeriesDetailTool(
    name="sonarr_get_series_by_id",
    description="Get detailed information about a specific series by its Sonarr ID. Returns complete series data including: episodeCount, episodeFileCount, seasons array (with monitored status and statistics per season), download percentages, quality profile, root folder path, and monitoring status. Essential for checking download status and season monitoring.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/series/{{id}}",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "includeSeasonImages": {"type": "boolean", "description": "Include season images"}
    }
)

sonarr_add_series = RequestsTool(
    name="sonarr_add_series",
    description="Add a new TV series to Sonarr. Requires TVDB ID, title, quality profile, and root folder path. Note: The full path will be {rootFolderPath}/{seriesTitle}.",
    method="POST",
    url_template=f"{SONARR_URL}/api/v3/series",
    headers={"X-Api-Key": SONARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Series title"},
            "tvdbId": {"type": "integer", "description": "TVDB ID of the series"},
            "tvRageId": {"type": "integer", "description": "TVRage ID of the series"},
            "tvMazeId": {"type": "integer", "description": "TVMaze ID of the series"},
            "tmdbId": {"type": "integer", "description": "TMDB ID of the series"},
            "imdbId": {"type": "string", "description": "IMDB ID of the series"},
            "titleSlug": {"type": "string", "description": "Title slug for the series"},
            "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
            "languageProfileId": {"type": "integer", "description": "Language profile ID (deprecated in v3)"},
            "rootFolderPath": {"type": "string", "description": "Root folder path"},
            "path": {"type": "string", "description": "Full path for the series"},
            "monitored": {"type": "boolean", "description": "Whether to monitor the series"},
            "monitorNewItems": {"type": "string", "description": "Monitor new items: all, none"},
            "seasonFolder": {"type": "boolean", "description": "Use season folders"},
            "useSceneNumbering": {"type": "boolean", "description": "Use scene numbering"},
            "seriesType": {"type": "string", "description": "Series type: standard, daily, or anime"},
            "tags": {"type": "array", "items": {"type": "integer"}, "description": "Tag IDs"},
            "seasons": {
                "type": "array",
                "description": "Season monitoring configuration",
                "items": {
                    "type": "object",
                    "properties": {
                        "seasonNumber": {"type": "integer", "description": "Season number"},
                        "monitored": {"type": "boolean", "description": "Whether to monitor this season"}
                    }
                }
            },
            "addOptions": {
                "type": "object",
                "properties": {
                    "ignoreEpisodesWithFiles": {"type": "boolean", "description": "Ignore episodes with files"},
                    "ignoreEpisodesWithoutFiles": {"type": "boolean", "description": "Ignore episodes without files"},
                    "monitor": {"type": "string", "description": "Monitor mode: all, future, missing, existing, pilot, firstSeason, latestSeason, none"},
                    "searchForMissingEpisodes": {"type": "boolean", "description": "Search for missing episodes after adding"},
                    "searchForCutoffUnmetEpisodes": {"type": "boolean", "description": "Search for cutoff unmet episodes"}
                }
            }
        },
        "required": ["title", "tvdbId", "qualityProfileId", "rootFolderPath"]
    }
)

sonarr_update_series = RequestsTool(
    name="sonarr_update_series",
    description="Update an existing series in Sonarr. Can update monitored status, quality profile, season folder setting, etc.",
    method="PUT",
    url_template=f"{SONARR_URL}/api/v3/series/{{id}}",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "moveFiles": {"type": "boolean", "description": "Move files when updating"}
    },
    body_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Series title"},
            "monitored": {"type": "boolean", "description": "Monitor status"},
            "monitorNewItems": {"type": "string", "description": "Monitor new items: all, none"},
            "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
            "seasonFolder": {"type": "boolean", "description": "Use season folders"},
            "useSceneNumbering": {"type": "boolean", "description": "Use scene numbering"},
            "seriesType": {"type": "string", "description": "Series type: standard, daily, anime"},
            "path": {"type": "string", "description": "Series path"},
            "tags": {"type": "array", "items": {"type": "integer"}, "description": "Tag IDs"},
            "seasons": {
                "type": "array",
                "description": "Season configuration",
                "items": {
                    "type": "object",
                    "properties": {
                        "seasonNumber": {"type": "integer"},
                        "monitored": {"type": "boolean"}
                    }
                }
            }
        }
    }
)

sonarr_delete_series = RequestsTool(
    name="sonarr_delete_series",
    description="Delete a series from Sonarr by its ID",
    method="DELETE",
    url_template=f"{SONARR_URL}/api/v3/series/{{id}}",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "deleteFiles": {"type": "boolean", "description": "Delete series files from disk"},
        "addImportListExclusion": {"type": "boolean", "description": "Add to import exclusion list"}
    }
)

sonarr_search_series = SonarrSearchTool(
    name="sonarr_search_series",
    description="Search for TV series to add to Sonarr using a search term. Returns detailed search results with TVDB/TMDB/IMDB IDs, status, network, series type, episode counts, and indicates if series is already in library.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/series/lookup",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "term": {
            "type": "string",
            "description": "Search term (series title or TVDB ID with 'tvdb:' prefix)",
            "required": True
        }
    }
)

sonarr_get_episodes = SonarrEpisodeListTool(
    name="sonarr_get_episodes",
    description="Get episodes for a series with download status. Returns array of episodes with: title, episode numbers, air dates, runtime, monitored status, hasFile (whether downloaded), and episodeFileId. Use seriesId (required) and optionally seasonNumber to filter. Essential for checking which specific episodes are downloaded or monitored.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/episode",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "seriesId": {"type": "integer", "description": "Series ID", "required": True},
        "seasonNumber": {"type": "integer", "description": "Filter by season number"},
        "episodeFileId": {"type": "integer", "description": "Filter by episode file ID"},
        "episodeIds": {"type": "array", "items": {"type": "integer"}, "description": "Filter by episode IDs"},
        "includeImages": {"type": "boolean", "description": "Include episode images"}
    }
)

sonarr_update_episode = RequestsTool(
    name="sonarr_update_episode",
    description="Update an episode (typically to change monitored status)",
    method="PUT",
    url_template=f"{SONARR_URL}/api/v3/episode/{{id}}",
    headers={"X-Api-Key": SONARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "seriesId": {"type": "integer", "description": "Series ID"},
            "tvdbId": {"type": "integer", "description": "TVDB episode ID"},
            "episodeFileId": {"type": "integer", "description": "Episode file ID"},
            "seasonNumber": {"type": "integer", "description": "Season number"},
            "episodeNumber": {"type": "integer", "description": "Episode number"},
            "title": {"type": "string", "description": "Episode title"},
            "airDate": {"type": "string", "description": "Air date"},
            "airDateUtc": {"type": "string", "description": "Air date UTC"},
            "overview": {"type": "string", "description": "Episode overview"},
            "monitored": {"type": "boolean", "description": "Monitor status"},
            "unverifiedSceneNumbering": {"type": "boolean", "description": "Unverified scene numbering"}
        }
    }
)

sonarr_get_queue = SonarrQueueTool(
    name="sonarr_get_queue",
    description="Get the current download queue in Sonarr with pagination support. Shows series, episode, download progress, quality, size, ETA, and protocol for each item in queue.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/queue",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "includeUnknownSeriesItems": {"type": "boolean", "description": "Include unknown series"}
    }
)

sonarr_delete_queue_item = RequestsTool(
    name="sonarr_delete_queue_item",
    description="Remove an item from the download queue",
    method="DELETE",
    url_template=f"{SONARR_URL}/api/v3/queue/{{id}}",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "removeFromClient": {"type": "boolean", "description": "Remove from download client"},
        "blocklist": {"type": "boolean", "description": "Add to blocklist"},
        "skipRedownload": {"type": "boolean", "description": "Skip automatic redownload"}
    }
)

sonarr_get_calendar = SonarrCalendarTool(
    name="sonarr_get_calendar",
    description="Get upcoming episode air dates in a date range. Returns episodes with air dates, titles, series information, runtime, and download status. REQUIRED: Use ISO format dates (YYYY-MM-DD) for start and end parameters. For 'this week' calculate the date range from current date. Set includeSeries=true to get series details with each episode. Use this to answer questions about upcoming releases.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/calendar",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "start": {"type": "string", "description": "Start date in ISO format (YYYY-MM-DD)"},
        "end": {"type": "string", "description": "End date in ISO format (YYYY-MM-DD)"},
        "unmonitored": {"type": "boolean", "description": "Include unmonitored episodes"},
        "includeSeries": {"type": "boolean", "description": "Include full series details with each episode"}
    }
)

sonarr_get_system_status = SonarrSystemStatusTool(
    name="sonarr_get_system_status",
    description="Get Sonarr system status including version, startup time, platform information, database details, and configuration settings.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/system/status",
    headers={"X-Api-Key": SONARR_API_KEY}
)

sonarr_get_quality_profiles = SonarrQualityProfilesTool(
    name="sonarr_get_quality_profiles",
    description="Get all quality profiles configured in Sonarr with upgrade settings, cutoff, minimum format score, and language preferences.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/qualityprofile",
    headers={"X-Api-Key": SONARR_API_KEY}
)

sonarr_get_root_folders = SonarrRootFoldersTool(
    name="sonarr_get_root_folders",
    description="Get all root folders configured in Sonarr with free/total space, accessibility status, and unmapped folders count.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/rootfolder",
    headers={"X-Api-Key": SONARR_API_KEY}
)

sonarr_trigger_series_search = RequestsTool(
    name="sonarr_trigger_series_search",
    description="Trigger a search for all missing episodes of a series",
    method="POST",
    url_template=f"{SONARR_URL}/api/v3/command",
    headers={"X-Api-Key": SONARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Command name: 'SeriesSearch'"},
            "seriesId": {"type": "integer", "description": "Series ID to search for"}
        },
        "required": ["name", "seriesId"]
    }
)

sonarr_trigger_episode_search = RequestsTool(
    name="sonarr_trigger_episode_search",
    description="Trigger a search for specific episodes",
    method="POST",
    url_template=f"{SONARR_URL}/api/v3/command",
    headers={"X-Api-Key": SONARR_API_KEY},
    body_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Command name: 'EpisodeSearch'"},
            "episodeIds": {"type": "array", "items": {"type": "integer"}, "description": "Episode IDs to search for"}
        },
        "required": ["name", "episodeIds"]
    }
)

sonarr_get_history = SonarrHistoryTool(
    name="sonarr_get_history",
    description="Get Sonarr history with pagination and filtering. Shows date, event type, series title, episode, quality, source indexer, and release name for all historical actions.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/history",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "sortKey": {"type": "string", "description": "Sort field"},
        "episodeId": {"type": "integer", "description": "Filter by episode ID"}
    }
)

sonarr_get_disk_space = SonarrDiskSpaceTool(
    name="sonarr_get_disk_space",
    description="Get disk space information for all root folders. Shows free and total space with percentage free for each storage location.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/diskspace",
    headers={"X-Api-Key": SONARR_API_KEY}
)

sonarr_get_wanted_missing = SonarrWantedTool(
    name="sonarr_get_wanted_missing",
    description="Get missing episodes that are monitored. Shows series, episode, title, air date, monitored status, and last search time for episodes not yet downloaded.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/wanted/missing",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "sortKey": {"type": "string", "description": "Sort field"},
        "includeSeries": {"type": "boolean", "description": "Include series details"}
    }
)

sonarr_get_wanted_cutoff = SonarrWantedTool(
    name="sonarr_get_wanted_cutoff",
    description="Get episodes that don't meet quality cutoff criteria. Shows series, episode, title, air date, monitored status, and last search time for episodes that need quality upgrades.",
    method="GET",
    url_template=f"{SONARR_URL}/api/v3/wanted/cutoff",
    headers={"X-Api-Key": SONARR_API_KEY},
    query_params_schema={
        "page": {"type": "integer", "description": "Page number"},
        "pageSize": {"type": "integer", "description": "Items per page"},
        "sortKey": {"type": "string", "description": "Sort field"},
        "includeSeries": {"type": "boolean", "description": "Include series details"}
    }
)

# =============================================================================
# TOOL COLLECTIONS
# =============================================================================

RADARR_TOOLS: List[RequestsTool] = [
    radarr_get_movies,
    radarr_get_movie_by_id,
    radarr_add_movie,
    radarr_update_movie,
    radarr_delete_movie,
    radarr_search_movies,
    radarr_get_queue,
    radarr_delete_queue_item,
    radarr_get_calendar,
    radarr_get_system_status,
    radarr_get_quality_profiles,
    radarr_get_root_folders,
    radarr_trigger_search,
    radarr_get_history,
    radarr_get_disk_space,
]

SONARR_TOOLS: List[RequestsTool] = [
    sonarr_get_series,
    sonarr_get_series_by_id,
    sonarr_add_series,
    sonarr_update_series,
    sonarr_delete_series,
    sonarr_search_series,
    sonarr_get_episodes,
    sonarr_update_episode,
    sonarr_get_queue,
    sonarr_delete_queue_item,
    sonarr_get_calendar,
    sonarr_get_system_status,
    sonarr_get_quality_profiles,
    sonarr_get_root_folders,
    sonarr_trigger_series_search,
    sonarr_trigger_episode_search,
    sonarr_get_history,
    sonarr_get_disk_space,
    sonarr_get_wanted_missing,
    sonarr_get_wanted_cutoff,
]

ALL_MEDIA_TOOLS: List[RequestsTool] = RADARR_TOOLS + SONARR_TOOLS

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_radarr_tools() -> List[RequestsTool]:
    """Get all Radarr tools"""
    return RADARR_TOOLS

def get_sonarr_tools() -> List[RequestsTool]:
    """Get all Sonarr tools"""
    return SONARR_TOOLS

def get_all_media_tools() -> List[RequestsTool]:
    """Get all media management tools (Radarr + Sonarr)"""
    return ALL_MEDIA_TOOLS

def configure_radarr(url: str, api_key: str) -> None:
    """
    Update Radarr configuration for all tools
    
    Args:
        url: Radarr base URL (e.g., "http://localhost:7878")
        api_key: Radarr API key
    """
    global RADARR_URL, RADARR_API_KEY
    old_url = RADARR_URL
    RADARR_URL = url
    RADARR_API_KEY = api_key
    
    # Update all Radarr tools
    for tool in RADARR_TOOLS:
        tool.url_template = tool.url_template.replace(old_url, url)
        tool.headers["X-Api-Key"] = api_key

def configure_sonarr(url: str, api_key: str) -> None:
    """
    Update Sonarr configuration for all tools
    
    Args:
        url: Sonarr base URL (e.g., "http://localhost:8989")
        api_key: Sonarr API key
    """
    global SONARR_URL, SONARR_API_KEY
    old_url = SONARR_URL
    SONARR_URL = url
    SONARR_API_KEY = api_key
    
    # Update all Sonarr tools
    for tool in SONARR_TOOLS:
        tool.url_template = tool.url_template.replace(old_url, url)
        tool.headers["X-Api-Key"] = api_key
