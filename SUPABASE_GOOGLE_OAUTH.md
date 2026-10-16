Google OAuth setup for HuevoHelper
==================================

Supabase project: https://supabase.com/dashboard/project/hzcexklqkpgkdbpzdhfx

1. Open Authentication -> Sign In / Providers -> Google and enable the provider.
2. In Google Cloud Console create an OAuth Client ID of type Web application.
3. Google Authorized redirect URI:
   https://hzcexklqkpgkdbpzdhfx.supabase.co/auth/v1/callback
4. Copy the client ID and client secret to the Supabase Google provider configuration.
5. Supabase Authentication -> URL Configuration -> Redirect URLs:
   http://127.0.0.1:8765/callback

Never commit the Google client secret or Supabase service-role key. OAuth will fail until provider credentials and the redirect allowlist are configured.
