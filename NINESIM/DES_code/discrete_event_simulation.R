###
### R code for discrete event simulation
### used to simulate conveyances passing through a port
### still learning this discrete simulation package
### code very much in development
### author: Jan Irvahn
### date: 4/23/2018
###


library(simmer)
set.seed(10212)


p <- 0.5             # probability of being sent to secondary
n <- 40              # number of cars
mean_arrival <- .1   # mean time between arrivals
tB<-2                # transit time to primary
mean_primary <- 12   # mean time in primary
tD<-2                # transit time to secondary
mean_secondary <-12  # mean time in secondary
tF<-2                # transit time to system exit

mql1 <- 10           # maximum queue length for primary lane 1
mql2 <- 10           # maximum queue length for primary lane 2
mql3 <- 10           # maximum queue length for primary lane 3
mqls <- 10           # maximum queue length for secondary:


car_traj <- trajectory(name = "car_trajectory") %>%
  set_attribute(keys = "slated_for_secondary", values = function() {rbinom(1,1,p)}) %>%
  set_attribute("start_time", function() {now(port)}) %>%
  log_(function() {paste("arrived: ", get_attribute(port, "start_time"))}) %>%
  seize("arrival") %>%
  release("arrival") %>%
  timeout(tB) %>%
  log_(function() {paste("arrived, primary: ", get_attribute(port, "arrived_primary"))}) %>%
  select(c("primary lane 1", "primary lane 2", "primary lane 3"), policy = "shortest-queue") %>%
  seize_selected() %>%
  log_(function() {paste("Waited in primary queue: ", now(port) - get_attribute(port, "arrived_primary"))}) %>%
  timeout(function() {rexp(1, 1/mean_primary)}) %>%
  release_selected() %>%
  log_(function() {paste("finished, primary: ", now(port))}) %>%
  branch(
    option = function() get_attribute(port, "slated_for_secondary"), continue = c(TRUE),
    trajectory() %>% 
      timeout(tD) %>%
      set_attribute("arrived_secondary", function() {now(port)}) %>%
      log_(function() {paste("arrived, secondary: ", get_attribute(port,"arrived_secondary"))}) %>%
      seize("secondary") %>%
      log_(function() {paste("Waited in secondary queue: ", now(port) - get_attribute(port, "arrived_secondary"))}) %>%
      timeout(function() {rexp(1, 1/mean_secondary)}) %>%
      release("secondary") %>%
      log_(function() {paste("finished, secondary: ", now(port))})
  ) %>%
  timeout(tF) %>%
  log_("out")

port <- simmer("port") %>%
  add_resource("arrival",1) %>%
  add_resource("primary lane 1", capacity = 1, queue_size = mql1) %>%
  add_resource("primary lane 2", capacity = 1, queue_size = mql2) %>%
  add_resource("primary lane 3", capacity = 1, queue_size = mql3) %>%
  add_resource("secondary",      capacity = 1, queue_size = mqls) %>%
  add_generator("car", car_traj, function() {c(0, rexp(n, 1/mean_arrival), -1)}, mon = 2) 

port %>% run(until=400)

port %>%
  get_mon_arrivals %>%
  dplyr::mutate(service_start_time = end_time - activity_time) %>%
  dplyr::arrange(start_time)

port %>%
  get_mon_resources %>%
  dplyr::arrange(time)

get_mon_attributes(port)
