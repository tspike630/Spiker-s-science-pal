-- sciencepal.ai cannot attach a file while this grant is missing.
-- The browser inserts into public.messages as `authenticated`. The insert
-- calls scrub_nested_message_unicode, and Postgres returns 42501 when that
-- role cannot EXECUTE the function. Run this in the Supabase SQL editor of
-- project dwkmdejtbxsavupvhjmc, as the database owner.
--
-- Read the body first. If the function is SECURITY DEFINER and writes tables,
-- do not grant it. Make the messages trigger SECURITY DEFINER owned by
-- postgres instead, and leave EXECUTE revoked from authenticated and anon.

SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'scrub_nested_message_unicode';

DO $$
DECLARE
  fn regprocedure;
  def text;
BEGIN
  SELECT p.oid::regprocedure, pg_get_functiondef(p.oid)
    INTO fn, def
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public'
    AND p.proname = 'scrub_nested_message_unicode';
  IF fn IS NULL THEN
    RAISE EXCEPTION 'scrub_nested_message_unicode not found in public';
  END IF;
  IF def ILIKE '%SECURITY DEFINER%' THEN
    RAISE EXCEPTION 'function is SECURITY DEFINER; fix the messages trigger instead of granting EXECUTE';
  END IF;
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %s TO authenticated, service_role',
    fn
  );
END $$;
