import { useState } from "react"
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material"
import LockOutlinedIcon from "@mui/icons-material/LockOutlined"
import { api, getApiKey, setApiKey } from "../lib/api"

interface Props {
  onAuthenticated: () => void
}

export function LoginGate({ onAuthenticated }: Props) {
  const [pw, setPw] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pw.trim()) return
    setSubmitting(true)
    setError(null)

    const previous = getApiKey()
    setApiKey(pw.trim())
    try {
      // Any authenticated endpoint works; orders is cheap.
      await api.listOrders({ limit: 1 })
      onAuthenticated()
    } catch (e) {
      // Restore previous key so we don't poison localStorage with bad creds.
      setApiKey(previous)
      const msg = (e as Error).message || "Invalid password"
      setError(
        /401|unauthor|invalid|forbidden/i.test(msg) ? "Invalid password" : msg,
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        px: 2,
      }}
    >
      <Container maxWidth="xs" disableGutters>
        <Card>
          <CardContent sx={{ p: 4 }}>
            <Stack alignItems="center" spacing={1.5} sx={{ mb: 3 }}>
              <Box
                sx={{
                  width: 56,
                  height: 56,
                  borderRadius: 2,
                  bgcolor: "primary.light",
                  color: "primary.dark",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <LockOutlinedIcon />
              </Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Medical Order Extractor
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center">
                Enter your access key to continue.
              </Typography>
            </Stack>

            <Box component="form" onSubmit={submit}>
              <TextField
                label="Password"
                type="password"
                value={pw}
                onChange={(e) => setPw(e.target.value)}
                autoFocus
                autoComplete="current-password"
                disabled={submitting}
                sx={{ mb: 2 }}
              />
              <Button
                type="submit"
                variant="contained"
                fullWidth
                size="large"
                disabled={submitting || !pw.trim()}
                startIcon={
                  submitting ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : undefined
                }
              >
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Container>

      <Snackbar
        open={!!error}
        autoHideDuration={3500}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        {error ? (
          <Alert
            severity="error"
            variant="filled"
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  )
}
