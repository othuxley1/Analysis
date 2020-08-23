# Monte Carlo Capacity Graphs
rm(list=ls())
library(ggplot2)
library(dplyr)
library(plotrix)
library(cowplot)

setwd("~/GitRepos/capacity_mismatch_paper/data")

########### MONTE CARLO HISTOGRAMS ###########

original_national_capacity <- 12.8 # GW

open_capacity_data <- function(filename, experiment_name,
                               original_national_capacity) {
  data <- filename %>%
    read.csv() %>%
    transmute(national_capacity..MW = national_capacity..MW. / 1000000) %>%
    mutate(Experiment = experiment_name) %>%
    mutate(percentage_error = ((national_capacity..MW -
                                  original_national_capacity) / 
                                 original_national_capacity) * 100)
  data$Experiment <- experiment_name
  
  mean_capacity <- mean(data$national_capacity..MW)
  stdev_capacity <- sd(data$national_capacity..MW)
  mape <- mean(data$percentage_error)
  result <- list("mape" = mape,
                 "mean" = mean_capacity,
                 "stdev" = stdev_capacity,
                 "data" = data,
                 "Experiment" = experiment_name)
  
  return(result)
  
}
AllE_UR <- open_capacity_data(
  "MC_results_v2_20200430_1000N.csv", "All Errors", 12.8
  )

AllE_NoUR <- open_capacity_data(
  "MC_results_v2_no_unreported_20200430_1000N.csv","All Errors", 12.8
  )

T0_UR <- open_capacity_data(
  "MC_results_v2_T0only_20200430_1000N.csv","T0", 12.8
)

T0_NoUR <- open_capacity_data(
  "MC_results_v2_T0only_no_unreported_20200430_1000N.csv","T0", 12.8
)


UR_data <- rbind(T0_UR$data, AllE_UR$data)
NoUR_data <- rbind(T0_NoUR$data, AllE_NoUR$data)

min_max <- function(df1, df2){
  maxx <- max(rbind(df1, df2)$national_capacity..MW)
  minn <- min(rbind(df1, df2)$national_capacity..MW)
  return(list("max" = maxx, "min" = minn))
}

graph_limits <- min_max(UR_data, NoUR_data)

head(subset(NoUR_data, Experiment== "All Errors No UR",
            select="national_capacity..MW"))


Experiment <- c("All Errors", "Unreported = 0")


df_vline <- data.frame(means, Experiment)

plot_histograms <- function(data1, data2, limits, colors){
  # calculate df_vline
  # plot histograms
  # return plot object
  
  # create dataframe to plot horizontal mean lines
  means <- c(data1$mean, data2$mean)
  Experiment <- c(data1$Experiment, data2$Experiment)
  df_vline <- data.frame("means" = means, "Experiment" = Experiment)
  
  mydata <- rbind(data1$data, data2$data)
  
  p <- ggplot(data=mydata, aes(x=national_capacity..MW, fill=Experiment, color=Experiment)) +
    geom_histogram(aes(y=..density..), alpha=0.6, position="identity", binwidth=0.05) +
    geom_vline(data = mydata,aes(xintercept = means,colour = Experiment)) +
    # geom_vline(xintercept=means[1], size=1.5) +
    # geom_vline(xintercept=means[2], size=1.5) +
    geom_vline(xintercept=12.8, color="black", size=1, linetype="dashed") +
    coord_flip() + theme_minimal_hgrid(12) +
    scale_y_continuous(
      # don't expand y scale at the lower end=
      expand = expansion(mult = c(0, 0))
    ) +
    scale_x_continuous(
      # don't expand y scale at the lower end
      expand = expansion(mult = c(0, 0)),
      limits=c(graph_limits$min, graph_limits$max + 0.5)
    ) +
    labs(y=NULL, x="National Capacity (GW)") +
    theme(axis.text.x = element_blank(),
          axis.ticks.x = element_blank()) +
    scale_fill_grey(start=0.8, end=0.2) +
    scale_color_grey(start=0.8, end=0.2)
    # annotate("text", label="Mean = 11.6 GW\nSD = 0.30 GW", x=11.3, y=1550, size=3, colour="black")
  return(p)
  
}

mycolors = c("#7a5195", "#ffa600")

p1 <- plot_histograms(T0_NoUR, AllE_NoUR, graph_limits, mycolors) + scale_y_reverse(expand = expansion(mult = c(0, 0)))
print(p1)
p2 <- plot_histograms(T0_UR, AllE_UR, graph_limits, mycolors) + theme(axis.title.y = element_blank(), axis.text.y = element_blank())
print(p2)

prow <- plot_grid(p1+ theme(legend.position="none"), p2+ theme(legend.position="none"), labels = "AUTO", label_fontfamily = "serif",
          label_fontface = "plain",
          label_colour = "black",
          label_x = 0.15, label_y = 1)
print(prow)

legend_b <- get_legend(
  p1 + 
    guides(color = guide_legend(nrow = 1)) +
    theme(legend.position = "bottom")
)

plot_grid(prow, legend_b, ncol = 1, rel_heights = c(1, .1))

### Horizontal Histograms ###


xmin <- 9.5
xmax <- 13
## Back to back
p3 <- ggplot(data= mydata, aes(x=national_capacity..MW)) +
  geom_histogram(data=subset(mydata, Experiment== "All Errors"), alpha=0.6, fill="#bc5090", color="#bc5090") +
  geom_vline(xintercept=means[1], size=2, colour="#bc5090") +
  geom_vline(xintercept=12.8, color="black", size=1, linetype="dashed") +
  coord_flip() + xlim(xmin, xmax) + theme_minimal_hgrid(12) +
  scale_y_continuous(
    # don't expand y scale at the lower end
    expand = expansion(mult = c(0, 0.05))
  ) + scale_y_reverse() +
  labs(y=NULL, x="National Capacity (GW)") +
  theme(axis.text.x = element_blank(),
        axis.ticks.x = element_blank()) + 
  annotate("text", label="Mean = 11.6 GW\nSD = 0.30 GW", x=11.3, y=1550, size=3, colour="black")

#annotate("text", label = "plot mpg vs. wt", x = 2, y = 15, size = 8, colour = "red")

p4 <- ggplot(data= mydata, aes(x=national_capacity..MW)) +
  geom_histogram(data=subset(mydata, Experiment== "Unreported = 0"), alpha=0.6, fill="#003f5c", color="#003f5c") +
  geom_vline(xintercept=12.8, color="black", size=1, linetype="dashed") +
  geom_vline(xintercept=means[2], size=2, colour="#003f5c") +
  coord_flip() + xlim(xmin, xmax) + theme_minimal_hgrid(12) +
  scale_y_continuous(
    # don't expand y scale at the lower end
    expand = expansion(mult = c(0, 0.05))
  ) +
  theme(axis.title.y = element_blank(), axis.text.y = element_blank()) + labs(y=NULL, x="National Capacity (GW)") +
  theme(axis.text.x = element_blank(),
        axis.ticks.x = element_blank()) +
  annotate("text", label="Mean = 10.8 GW\nSD = 0.27 GW", x=11.3, y=1600, size=3, colour="black")

plot_grid(p3, p4, labels = "AUTO", label_fontfamily = "serif",
          label_fontface = "plain",
          label_colour = "black")

########### T0 HISTOGRAMS ###########

T0_capacities_na <- read.csv("capacities.csv")
count_matched_na <- nrow(T0_capacities_na)

T0_capacities <- na.omit(T0_capacities_na)
count_matched <- nrow(T0_capacities)

T0_capacities$Bias..Error <- T0_capacities$SM.Capacity -
  T0_capacities$REPD.Capacity
T0_capacities$Normalised..Bias..Error <- 
  (T0_capacities$Bias..Error / T0_capacities$SM.Capacity) * 100

T0_capacities_no_zeros <- T0_capacities[T0_capacities$Bias..Error != 0,]
count_no_zeros = nrow(T0_capacities_no_zeros)

non_zero_bias_frac = (count_no_zeros/count_matched) * 100
zero_bias_frac = 100 - non_zero_bias_frac

p2 <- ggplot(data=T0_capacities, aes(x=Normalised..Bias..Error)) +
  geom_histogram(alpha=0.6, bins=40, position="identity") +
  geom_vline(xintercept=12.8, color="black", size=1, linetype="dashed") +
  
  scale_y_continuous(
    # don't expand y scale at the lower end
    expand = expansion(mult = c(0, 0.05)),
    limits = c(0, 410)
  ) +
  theme_minimal_hgrid(12) +
  labs(x="Normalised Bias Error (%)", y="Count")

p3 <- ggplot(data=T0_capacities_no_zeros, aes(x=Normalised..Bias..Error)) +
  geom_histogram(alpha=0.6, bins=40, position="identity") +
  scale_y_continuous(
    # don't expand y scale at the lower end
    expand = expansion(mult = c(0, 0.05)),
    limits = c(0, 410)
  ) +
  theme_minimal_hgrid(12) +
  labs(x="Normalised Bias Error (%)", y="Count")

plot_grid(p2, p3, labels = "AUTO", label_fontfamily = "serif",
          label_fontface = "plain", label_colour = "black", align="h")

########### Unreported Simulation Results ###########

options(scipen = 100, digits = 4)


average_FIT <- read.csv("FIT_payment_rate_group_by_date.csv")
unreported_probability <- read.csv("probability_unreported.csv")
results <- read.csv("unreported_results.csv")


results$Date <- as.Date(results$Date, format = "%Y-%m-%d")
# results

system_sizes <- unique(results$System.Size)

# select only count values (remove cumulative count rows)
results = results[
  which(results$Status == "Cumulative Count" |results$Status == "Cumulative Count Unreported alpha*exp(-beta*x) + theta"),
  ]





p4 <- ggplot(data=results[which(results$System.Size == system_sizes[1]),],
             aes(x=Date, y=Cumulative.Count, fill=Status, color=Status)) +
  geom_area(aes(fill=Status), position= position_stack(reverse = T)) +
#  scale_y_log10(limits=c(1, 1.2e+12)) +
#  scale_y_continuous(trans = 'log10') +
  theme_half_open(12) +
  scale_fill_grey(
    start = 0.8,
    end = 0.2,
    na.value = "red",
    aesthetics = "fill",
    name = "Source:  "
  ) +
  scale_colour_grey(
    start = 0.2,
    end = 0.8,
    na.value = "red",
    aesthetics = "colour",
    name = "Source:  ",
    labels = c("Reported (Accredited + Unaccredited)  ", "Unreported ")
  )  + ylab("Count") +
scale_x_date(date_breaks = "years" , date_labels = "%Y") + theme(axis.text.x = element_text(angle = 90, hjust = 1))


p5 <- ggplot(data=results[which(results$System.Size == system_sizes[2]),],
             aes(x=Date, y=Cumulative.Count, fill=Status, color=Status)) +
  geom_area(aes(fill=Status),  position= position_stack(reverse = T)) +
#  scale_y_log10(limits=c(1, 1.2e12)) +
  theme_half_open(12) +ylab(NULL) +
  scale_fill_grey(
    start = 0.8,
    end = 0.2,
    na.value = "red",
    aesthetics = "fill",
    name = "Source:  "
  ) +
  scale_colour_grey(
    start = 0.2,
    end = 0.8,
    na.value = "red",
    aesthetics = "colour",
    name = "Source:  ",
    labels = c("Reported (Accredited + Unaccredited)  ", "Unreported ")
  ) + scale_x_date(date_breaks = "years" , date_labels = "%Y") + theme(axis.text.x = element_text(angle = 90, hjust = 1))

p6 <- ggplot(data=results[which(results$System.Size == system_sizes[3]),],
             aes(x=Date, y=Cumulative.Count, fill=Status, color=Status)) +
  geom_area(aes(fill=Status),  position= position_stack(reverse = T)) +
#  scale_y_log10(limits=c(1, 1.2e12)) +
  theme_half_open(12) +
  scale_fill_grey(
    start = 0.8,
    end = 0.2,
    na.value = "red",
    aesthetics = "fill",
    name = "Source:  "
  ) +
  scale_colour_grey(
    start = 0.2,
    end = 0.8,
    na.value = "red",
    aesthetics = "colour",
    name = "Source:  ",
    labels = c("Reported (Accredited + Unaccredited)  ", "Unreported ")
  ) + ylab("Count") +
 scale_x_date(date_breaks = "years" , date_labels = "%Y") + theme(axis.text.x = element_text(angle = 90, hjust = 1))

p7 <- ggplot(data=results[which(results$System.Size == system_sizes[4]),],
             aes(x=Date, y=Cumulative.Count, fill=Status, color=Status)) +
  geom_area(aes(fill=Status),  position= position_stack(reverse = T)) +
#  scale_y_log10(limits=c(1, 1.2e12)) +
  theme_half_open(12) + ylab(NULL) +
  scale_fill_grey(
    start = 0.8,
    end = 0.2,
    na.value = "red",
    aesthetics = "fill",
    name = "Source:  "
  ) +
  scale_colour_grey(
    start = 0.8,
    end = 0.2,
    na.value = "red",
    aesthetics = "colour",
    name = "Source:  ",
    labels = c("Reported (Accredited + Unaccredited)  ", "Unreported ")
  ) + scale_x_date(date_breaks = "years" , date_labels = "%Y") + theme(axis.text.x = element_text(angle = 90, hjust = 1))

count_legend <- get_legend(
  p7 + guides(color = guide_legend(nrow = 1)) +
    theme(legend.position = "bottom")
)

count_plots <- plot_grid(
  p4 + theme(legend.position="none"),
  p5 + theme(legend.position="none"),
  p6 + theme(legend.position="none"),
  p7 + theme(legend.position="none"),
  labels = "AUTO", label_fontfamily = "serif", label_size = 12,
  label_fontface = "plain", label_colour = "black", align="h",
  label_x = 0.4, label_y = 0.6,
  hjust = -0.5, vjust = -0.5
)

print(count_plots)

plot_grid(count_plots, count_legend, ncol = 1, rel_heights = c(1, .1))


########### Unaccredited rate ###########

library(latex2exp)

unaccredited_data = read.csv("Unaccredited_with_FIT_rate.csv")
unaccredited_data$Date <- as.Date(unaccredited_data$Date, format = "%Y-%m-%d")

p8 <- ggplot(data=unaccredited_data, aes(x=Date, y=Unaccredited)) +
  geom_line()

print(p8)

#select after 2010-04-01
unaccredited_data <- unaccredited_data[which(unaccredited_data$Date > as.Date('2010-03-01', "%Y-%m-%d")), ]

unaccredited_data$probability <- (unaccredited_data$Difference.Unaccredited. / unaccredited_data$Difference.TOTAL.) * 100

lin.model = lm(log(probability)~log(FIT.Rate..p.))


p9 <- ggplot(data=unaccredited_data, aes(x=FIT.Rate..p., y=probability)) +
  geom_point()


p9 <- ggplot(data=unaccredited_data, aes(x=log(FIT.Rate..p.), y=log(probability))) +
  geom_point() +
  abline(lm(log(probability)~log(FIT.Rate..p.), data=unaccredited_data))

print(p9)

theta.0 <- min(unaccredited_data$probability) * 0.5

model.0  <- lm(log(probability-theta.0)~FIT.Rate..p., data=unaccredited_data)
alpha.0 <- exp(coef(model.0)[1])
beta.0 <- coef(model.0)[2]

start <- list(alpha=alpha.0, beta=beta.0, theta=theta.0)

mymodel = nls(probability ~ alpha * exp(beta * FIT.Rate..p.) + theta, data=unaccredited_data, start=start)

#eq <- (y) == coef(mymodel)[1] * e^(coef(mymodel)[2] * (x)) + coef(mymodel)[3]

p9 <- ggplot(data=unaccredited_data, aes(x=FIT.Rate..p., y=probability)) +
  geom_point() +
  geom_smooth(method = "nls", 
              method.args = list(formula = y ~ alpha * exp(beta * x) + theta,
                                 start = list(alpha=alpha.0, beta=beta.0, theta=theta.0)), 
              data = unaccredited_data,
              se = FALSE,
              ) +
  ylab("Probabiility of under-reporting (%)") + xlab("Fit rate (p)") + 
  theme_half_open()
#  geom_text(x = 25, y = 300, label = ("y = 90 * e^{-0.54 * x} + 10"))
  
print(p9)

# preparing fits data
fits <- unaccredited_data %>%
  select(Date, FITs..not.standalone., FiTs..standalone.) %>%
  data.frame()
fits$Date <- as.Date(fits$Date)
fits$cumulative_count <- fits$FITs..not.standalone.+ fits$FiTs..standalone.
fits$funding_accreditation <- "FITs"
fits <- fits %>%
  select(Date, cumulative_count, funding_accreditation) %>%
  data.frame()
# preparing RO data
RO <- unaccredited_data %>%
  select(Date, RO..ground.mounted., RO..not.ground.mounted.) %>%
  data.frame()
RO$Date <- as.Date(RO$Date)
RO$cumulative_count <- RO$RO..ground.mounted. + RO$RO..not.ground.mounted.
RO$funding_accreditation <- "RO"
RO <- RO %>%
  select(Date, cumulative_count, funding_accreditation) %>%
  data.frame()
# preparing unaccredited
ua <- unaccredited_data %>%
  select(Date, Unaccredited) %>%
  data.frame()
ua$Date <- as.Date(ua$Date)
ua$cumulative_count <- ua$Unaccredited
ua$funding_accreditation <- "Unaccredited"
ua <- ua %>%
  select(Date, cumulative_count, funding_accreditation) %>%
  data.frame()

stacked_data <-rbind(fits, RO, ua)

stacked_data$cumulative_count <- stacked_data$cumulative_count / 1000000

p10 <- ggplot(data=stacked_data, aes(x=Date, y=cumulative_count,
                                          fill=funding_accreditation,
                                          color=funding_accreditation)) +
  geom_area(aes(fill=funding_accreditation),
            position= position_stack(reverse = T)) +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.05)),
    position = "right"
  ) +
  scale_fill_grey(
    start = 0.6,
    end = 0.8,
    na.value = "red",
    aesthetics = "fill",
    name = "Funding Accreditation:  "
  ) +
  scale_colour_grey(
    start = 0.6,
    end = 0.8,
    na.value = "red",
    aesthetics = "colour",
    name = "Funding Accreditation:  "
  ) +
  ylab("Count") + xlab("Date") +
  scale_x_date(date_breaks = "years" , date_labels = "%Y") +
  theme_minimal_hgrid() + theme(axis.text.x = element_text(angle = 90, hjust = 1))

print(p10)

p11 <- ggplot(data=unaccredited_data, aes(x=Date, y=FIT.Rate..p.)) +
  geom_line() + theme_half_open() + theme(axis.title.x=element_blank(),
                                          axis.text.x=element_blank(),
                                          axis.ticks.x=element_blank()) +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.05))
  ) + ylab("Fit Rate (p)") +xlab(NULL)
print(p11)

aligned_plots <- align_plots(p10 + theme(legend.position="none"),
                             p11, align="hv", axis="tblr")
funding_count_plot <- ggdraw(aligned_plots[[1]]) + draw_plot(aligned_plots[[2]])


funding_legend <- get_legend(
  p10 + guides(color = guide_legend(nrow = 1)) +
    theme(legend.position = "bottom")
)

plot_grid(funding_count_plot, funding_legend, ncol = 1, rel_heights = c(1, .1))

############### PV Generation Plots ##############################
library(zoo)
library(lubridate)

pv_gen_data <- read.csv("monthly_sum_pvgen.csv")


pv_gen_data$Date <- as.Date(pv_gen_data$Date, "%m-%d-%Y")

pv_gen_data$generation_TWh <- pv_gen_data$Sum.generation_MWh. / 1e6

pv_gen_data[which(pv_gen_data$version_id == 262), "experiment"] <- "T0 Only"
pv_gen_data[which(pv_gen_data$version_id == 264), "experiment"] <- "T0 Only No Unreported"
pv_gen_data[which(pv_gen_data$version_id == 265), "experiment"] <- "All Errors"
pv_gen_data[which(pv_gen_data$version_id == 266), "experiment"] <- "All Errors No Unreported"

# exclude data after 2020-01-01
pv_gen_data <- data.frame(pv_gen_data[which(pv_gen_data$Date < "2020-01-01"),])


p12 <- ggplot(data=pv_gen_data, aes(x=Date, y=generation_TWh)) +
  geom_line(aes(color = experiment), size=1) +
  scale_colour_grey(
    start = 0.2,
    end = 0.8,
    na.value = "red",
    aesthetics = "colour",
    name = "Experiment:  "
  ) +
  scale_y_continuous(breaks=seq(0,2,0.2), name="Monthly Generation (TWh)", limits=c(0,1.8)) +
  scale_x_date(date_breaks = "years" , date_labels = "%Y") +
  theme_half_open(14) +
  theme(panel.grid.major.y = element_line(color="grey", size=0.5))

print(p12)



max_day <- read.csv("max_pvgen_20200420.csv")

