// Firefox configuration for containerized environments
// Essential settings to fix container-specific issues

// Completely disable update system (prevents locale file errors)
user_pref("app.update.enabled", false);
user_pref("app.update.auto", false);
user_pref("app.update.service.enabled", false);
user_pref("app.update.url", "");
user_pref("app.update.url.manual", "");
user_pref("app.update.url.details", "");
user_pref("app.update.staging.enabled", false);
user_pref("app.update.channel", "");
user_pref("app.update.background.scheduling.enabled", false);
user_pref("extensions.update.url", "");
user_pref("general.useragent.updates.enabled", false);

// Disable telemetry and data reporting
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.server", "");
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);

// Fix graphics rendering in container
user_pref("layers.acceleration.disabled", true);
user_pref("gfx.webrender.enabled", false);
user_pref("gfx.webrender.all", false);

// Completely disable new tab page features
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.highlights", false);
user_pref("browser.newtabpage.activity-stream.feeds.snippets", false);
user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
user_pref("browser.newtabpage.activity-stream.telemetry", false);
user_pref("browser.newtabpage.activity-stream.feeds.system.topstories", false);
user_pref("browser.newtabpage.activity-stream.default.sites", "");
user_pref("browser.newtabpage.activity-stream.discoverystream.enabled", false);
user_pref("browser.newtabpage.activity-stream.showSearch", false);
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);

// Use about:blank for new tabs and homepage
user_pref("browser.startup.homepage", "about:blank");
user_pref("browser.startup.page", 0);
user_pref("browser.startup.homepage_override.mstone", "ignore");

// Disable network connectivity checks
user_pref("network.connectivity-service.enabled", false);
user_pref("network.captive-portal-service.enabled", false);

// Configure Remote Settings (reduce errors while maintaining UI functionality)
user_pref("services.settings.poll_interval", 31536000); // 1 year in seconds - minimize polling
user_pref("services.settings.default_sync_interval", 31536000); // 1 year in seconds
user_pref("services.settings.server", "data:,"); // Empty server to prevent network requests
user_pref("services.settings.load_dump", true); // Use local dumps
user_pref("browser.region.update.enabled", false); // Prevent region updates
user_pref("app.normandy.enabled", false); // Disable Normandy/Shield
user_pref("app.normandy.api_url", "");

// Disable search engine features (to prevent icon errors)
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.search.update", false);
user_pref("browser.search.geoSpecificDefaults", false);
user_pref("browser.search.geoSpecificDefaults.url", "");
user_pref("browser.search.separatePrivateDefault.ui.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);
user_pref("browser.urlbar.suggest.engines", false);
user_pref("browser.urlbar.quicksuggest.enabled", false);

// Disable all Firefox intro/onboarding screens
user_pref("browser.aboutwelcome.enabled", false);
user_pref("trailhead.firstrun.didSeeAboutWelcome", true);
user_pref("browser.startup.firstrunSkipsHomepage", true);
user_pref("browser.tabs.warnOnClose", false);
user_pref("browser.tabs.warnOnOpen", false);
user_pref("browser.contentblocking.introduction.shown", true);
user_pref("browser.discovery.enabled", false);
user_pref("browser.engagement.recently_visited_sites.enabled", false);
user_pref("browser.laterrun.enabled", false);
user_pref("browser.uitour.enabled", false);
user_pref("browser.uitour.url", "");
user_pref("datareporting.policy.firstRunURL", "");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("startup.homepage_override_url", "");

// Miscellaneous error prevention
user_pref("browser.safebrowsing.malware.enabled", false);
user_pref("browser.safebrowsing.phishing.enabled", false);
user_pref("browser.safebrowsing.downloads.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("extensions.systemAddon.update.enabled", false);
user_pref("extensions.update.enabled", false);
user_pref("extensions.webservice.discoverURL", "");
user_pref("extensions.getAddons.cache.enabled", false);
user_pref("browser.bookmarks.restore_default_bookmarks", false);
user_pref("browser.places.importBookmarksHTML", false);

// Fix for "update.locale" file not found error
user_pref("intl.locale.requested", "en-US");
