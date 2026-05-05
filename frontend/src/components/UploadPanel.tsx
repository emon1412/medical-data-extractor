import { useRef, useState } from "react"
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  Stack,
  Typography,
} from "@mui/material"
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined"
import CloudUploadIcon from "@mui/icons-material/CloudUploadOutlined"
import DescriptionIcon from "@mui/icons-material/DescriptionOutlined"
import { api } from "../lib/api"
import type { ExtractionResponse } from "../types/api"
import { DocumentDetailsView } from "./DocumentDetailsView"
import { PdfPreview } from "./PdfPreview"

interface Props {
  onOrderCreated?: () => void
  onToast?: (msg: string, kind?: "success" | "error") => void
  onViewOrders?: () => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(2)} MB`
}

const confidenceColor = (c: string): "success" | "warning" | "error" => {
  if (c === "high") return "success"
  if (c === "medium") return "warning"
  return "error"
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={2} sx={{ mb: 0.75 }}>
      <Typography
        variant="body2"
        sx={{ minWidth: 140, fontWeight: 600 }}
        color="text.secondary"
      >
        {label}
      </Typography>
      <Box sx={{ flex: 1 }}>
        {value ?? (
          <Typography component="span" color="text.disabled">
            —
          </Typography>
        )}
      </Box>
    </Stack>
  )
}

export function UploadPanel({ onOrderCreated, onToast, onViewOrders }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ExtractionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [showDetails, setShowDetails] = useState(true)

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  const upload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const r = await api.extractPdf(file, true)
      setResult(r)
      if (r.order_id) {
        onToast?.("Order created from extraction", "success")
        onOrderCreated?.()
      } else {
        onToast?.("Extraction complete", "success")
      }
    } catch (e) {
      const msg = (e as Error).message
      setError(msg)
      onToast?.(msg, "error")
    } finally {
      setUploading(false)
    }
  }

  const reset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ""
  }

  return (
    <>
      <Box sx={{ mb: 4, textAlign: "center" }}>
        <Typography variant="h3" sx={{ fontWeight: 700 }}>
          Extract patient data from a PDF
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1.5 }}>
          Drop a medical order and the relevant data will be extracted
        </Typography>
      </Box>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") inputRef.current?.click()
            }}
            sx={{
              cursor: "pointer",
              borderRadius: 3,
              border: "2px dashed",
              borderColor: dragging ? "primary.main" : "divider",
              bgcolor: dragging ? "primary.light" : "transparent",
              p: 5,
              textAlign: "center",
              transition: "all 0.15s",
              "&:hover": {
                borderColor: "primary.light",
                bgcolor: "action.hover",
              },
            }}
          >
            {file ? (
              <Stack
                direction="row"
                spacing={2}
                alignItems="center"
                justifyContent="center"
              >
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: "primary.light",
                    color: "primary.dark",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <DescriptionIcon />
                </Box>
                <Box sx={{ textAlign: "left" }}>
                  <Typography sx={{ fontWeight: 600 }}>{file.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {formatBytes(file.size)}
                  </Typography>
                </Box>
              </Stack>
            ) : (
              <Stack alignItems="center" spacing={1.5}>
                <Box
                  sx={{
                    width: 56,
                    height: 56,
                    borderRadius: 3,
                    bgcolor: "primary.light",
                    color: "primary.dark",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <CloudUploadIcon fontSize="large" />
                </Box>
                <Typography sx={{ fontWeight: 600 }}>
                  Drop a PDF here, or click to browse
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Up to 10 MB max size
                </Typography>
              </Stack>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              hidden
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </Box>

          <Stack
            direction="row"
            spacing={1.5}
            justifyContent="center"
            sx={{ mt: 3 }}
          >
            <Button
              variant="contained"
              size="large"
              disabled={!file || uploading}
              onClick={upload}
              startIcon={
                uploading ? (
                  <CircularProgress size={16} color="inherit" />
                ) : undefined
              }
            >
              {uploading ? "Extracting…" : "Extract data"}
            </Button>
            {file && (
              <Button variant="outlined" disabled={uploading} onClick={reset}>
                Clear
              </Button>
            )}
          </Stack>

          {error && (
            <Alert severity="error" sx={{ mt: 2.5 }}>
              {error}
            </Alert>
          )}
        </CardContent>
      </Card>

      {(file || result) && (
        <Box
          sx={{
            mt: 3,
            display: "grid",
            gap: 3,
            gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
          }}
        >
          <Box>{file && <PdfPreview file={file} maxPages={4} />}</Box>
          <Box>
            {result && (
              <Card
                sx={{
                  borderLeft: "4px solid",
                  borderLeftColor: "success.main",
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Stack
                    direction="row"
                    spacing={2}
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 2, flexWrap: "wrap", rowGap: 1 }}
                  >
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CheckCircleIcon color="success" />
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Extraction complete
                      </Typography>
                    </Stack>
                    {result.order_id && onViewOrders && (
                      <Button variant="outlined" onClick={onViewOrders}>
                        View in Orders →
                      </Button>
                    )}
                  </Stack>

                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      display: "block",
                      mb: 1,
                      fontWeight: 600,
                      letterSpacing: 1,
                      textTransform: "uppercase",
                    }}
                  >
                    Patient
                  </Typography>
                  <FieldRow
                    label="First name"
                    value={result.extracted.first_name}
                  />
                  <FieldRow
                    label="Last name"
                    value={result.extracted.last_name}
                  />
                  <FieldRow
                    label="Date of birth"
                    value={result.extracted.date_of_birth}
                  />
                  <FieldRow
                    label="Confidence"
                    value={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip
                          label={result.extracted.confidence}
                          size="small"
                          color={confidenceColor(result.extracted.confidence)}
                          variant="outlined"
                        />
                        <Typography variant="body2" color="text.secondary">
                          via {result.extracted.source}
                        </Typography>
                      </Stack>
                    }
                  />
                  {result.order_id && (
                    <FieldRow
                      label="Order ID"
                      value={
                        <Chip
                          label={result.order_id}
                          size="small"
                          sx={{
                            fontFamily: "ui-monospace, monospace",
                            fontSize: 11,
                            height: 20,
                          }}
                        />
                      }
                    />
                  )}

                  {result.extracted.document && (
                    <>
                      <Divider sx={{ my: 2.5 }} />
                      <Button
                        fullWidth
                        onClick={() => setShowDetails((v) => !v)}
                        sx={{
                          justifyContent: "space-between",
                          color: "text.secondary",
                          fontWeight: 600,
                          letterSpacing: 1,
                          textTransform: "uppercase",
                          fontSize: 12,
                          mb: 1.5,
                        }}
                      >
                        <span>Full document details</span>
                        <span>{showDetails ? "−" : "+"}</span>
                      </Button>
                      <Collapse in={showDetails}>
                        <DocumentDetailsView
                          details={result.extracted.document}
                        />
                      </Collapse>
                    </>
                  )}
                </CardContent>
              </Card>
            )}
            {!result && file && (
              <Box
                sx={{
                  border: "1px dashed",
                  borderColor: "divider",
                  borderRadius: 2,
                  p: 4,
                  textAlign: "center",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Click <strong>Extract patient data</strong> above to pull
                  structured fields from this document.
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      )}
    </>
  )
}
