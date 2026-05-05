import { useEffect, useRef, useState } from "react"
import { Alert, Box, Typography } from "@mui/material"
import * as pdfjsLib from "pdfjs-dist"
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url"

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

interface Props {
  file: File | null
  /** Cap on pages rendered. Avoids massive memory use on long PDFs. */
  maxPages?: number
}

export function PdfPreview({ file, maxPages = 4 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [pageCount, setPageCount] = useState(0)
  const [renderedPages, setRenderedPages] = useState(0)

  useEffect(() => {
    if (!file || !containerRef.current) return
    const container = containerRef.current
    container.innerHTML = ""
    setError(null)
    setPageCount(0)
    setRenderedPages(0)

    let cancelled = false
    let loadingTask: ReturnType<typeof pdfjsLib.getDocument> | null = null

    ;(async () => {
      try {
        const buffer = await file.arrayBuffer()
        if (cancelled) return
        loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(buffer) })
        const pdf = await loadingTask.promise
        if (cancelled) return

        const total = Math.min(pdf.numPages, maxPages)
        setPageCount(pdf.numPages)

        for (let pageNum = 1; pageNum <= total; pageNum++) {
          if (cancelled) return
          const page = await pdf.getPage(pageNum)
          const viewport0 = page.getViewport({ scale: 1 })
          const containerWidth = container.clientWidth || 480
          const scale =
            (containerWidth / viewport0.width) *
            Math.min(window.devicePixelRatio || 1, 2)
          const viewport = page.getViewport({ scale })

          const canvas = document.createElement("canvas")
          canvas.width = viewport.width
          canvas.height = viewport.height
          canvas.style.width = `${containerWidth}px`
          canvas.style.height = `${(viewport.height / viewport.width) * containerWidth}px`
          canvas.style.borderRadius = "8px"
          canvas.style.border = "1px solid #e2e8f0"
          canvas.style.marginBottom = "12px"
          canvas.style.background = "#fff"
          canvas.style.boxShadow = "0 1px 2px rgba(15,23,42,0.05)"
          container.appendChild(canvas)

          const ctx = canvas.getContext("2d")
          if (!ctx) continue
          await page.render({ canvasContext: ctx, viewport, canvas }).promise
          if (cancelled) return
          setRenderedPages(pageNum)
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message)
      }
    })()

    return () => {
      cancelled = true
      loadingTask?.destroy()
    }
  }, [file, maxPages])

  if (!file) return null

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography
          variant="caption"
          sx={{ fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}
          color="text.secondary"
        >
          Preview
        </Typography>
        {pageCount > 0 && (
          <Typography variant="caption" color="text.secondary">
            {renderedPages} / {Math.min(pageCount, maxPages)}
            {pageCount > maxPages && ` of ${pageCount}`} pages
          </Typography>
        )}
      </Box>
      {error ? (
        <Alert severity="error">Could not render preview: {error}</Alert>
      ) : (
        <Box
          ref={containerRef}
          sx={{
            maxHeight: "80vh",
            overflowY: "auto",
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "grey.50",
            p: 1.5,
          }}
        />
      )}
    </Box>
  )
}
