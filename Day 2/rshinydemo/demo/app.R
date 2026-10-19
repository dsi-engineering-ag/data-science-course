
# shiny::runApp('~/Code/training/data-science-course/Day 2/rshinydemo/demo/app.R')

library(shiny) 

ui <- fluidPage(
  
  titlePanel("Iris Demo"),
  
  sidebarLayout(
    
    sidebarPanel(
      sliderInput(inputId = "bins",
                  label = "Number of bins:",
                  min = 1,
                  max = 15,
                  value = 3)
    ),
    
    mainPanel(
      plotOutput(outputId = "distSepalPlot"),
      plotOutput(outputId = "distPetalPlot"),
      DT::dataTableOutput("table")
    )
  )
)

# Define server logic required to draw a histogram ----
server <- function(input, output) {
  
  output$distSepalPlot <- renderPlot({
    
    x    <- iris$Sepal.Length
    bins <- seq(min(x), max(x), length.out = input$bins + 1)
    
    hist(x, breaks = bins, col = "#75AADB", border = "white",
         xlab = "Sepal Length",
         main = "Histogram of Sepal Length")
    
  })
  output$distPetalPlot <- renderPlot({
    
    x    <- iris$Petal.Length
    bins <- seq(min(x), max(x), length.out = input$bins + 1)
    hist(x, breaks = bins, col = "#75AADB", border = "white",
         xlab = "Petal Length",
         main = "Histogram of Petal Length")
    
  })
    output$table <- DT::renderDataTable(DT::datatable({
      iris
    }))
}


shinyApp(ui = ui, server = server)

