### Pipeline Gates

DESIGN: -    
# Plan project once all design comments are resolved
PLAN: Auto                      
# Assign tasks to agents once plan is created
ASSIGN: Auto                    
# Perform code review once code implementation is completed and tests pass
IMPLEMENT.CODEREVIEW: Auto         
# Apply code review suggestions once code review is completed
IMPLEMENT.CODEREVIEWCHANGES: Auto         
# Merge code once code review suggestions are applied and tests pass
IMPLEMENT.MERGE: Auto   
# Deploy once all tasks are implemented      
DEPLOY: Auto            
# Start servicing agents once service is deployed
SERVICE: Auto           


