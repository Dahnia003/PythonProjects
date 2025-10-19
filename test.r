# test.R
library(ggplot2)

cat("Starting analysis...\n")

df <- read.csv("fire_clean.csv", stringsAsFactors = FALSE)
df$type <- trimws(as.character(df$type))

hms_to_minutes <- function(s) {
  parts <- strsplit(as.character(s), ":")[[1]]
  if (length(parts) != 3) return(NA_real_)
  h <- as.numeric(parts[1]); m <- as.numeric(parts[2]); sec <- as.numeric(parts[3])
  h * 60 + m + sec / 60
}
df$duration_min <- sapply(df$duration, hms_to_minutes)

# 1) Frequency by type
type_counts <- sort(table(df$type), decreasing = TRUE)
p1 <- ggplot(
  data.frame(type = names(type_counts), count = as.vector(type_counts)),
  aes(x = reorder(type, -count), y = count)
) +
  geom_bar(stat = "identity") +
  labs(title = "EMS/Fire Call Types (Frequency)", x = "Call Type", y = "Count") +
  theme(axis.text.x = element_text(angle = 60, hjust = 1))
ggsave("type_frequency.png", p1, width = 10, height = 6, dpi = 120)

# 2) Median duration for top 15 types
top_types <- names(type_counts)[1:min(15, length(type_counts))]
dur_by_type <- tapply(df$duration_min[df$type %in% top_types],
                      df$type[df$type %in% top_types],
                      median, na.rm = TRUE)
dur_by_type <- sort(dur_by_type, decreasing = TRUE)
p2 <- ggplot(
  data.frame(type = names(dur_by_type), median_duration = as.vector(dur_by_type)),
  aes(x = reorder(type, -median_duration), y = median_duration)
) +
  geom_bar(stat = "identity") +
  labs(title = "Median Call Duration by Type, Top 15", x = "Call Type", y = "Median Minutes") +
  theme(axis.text.x = element_text(angle = 60, hjust = 1))
ggsave("median_duration_top15.png", p2, width = 10, height = 6, dpi = 120)

cat("Saved: type_frequency.png and median_duration_top15.png\n")
