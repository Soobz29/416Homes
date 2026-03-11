from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

@app.get('/listings')
def get_listings():
    return [
        {'id': '1', 'address': '123 King St W, Toronto', 'price': 899000, 'bedrooms': '2', 'bathrooms': '2', 'area': '950', 'source': 'realtor_ca'},
        {'id': '2', 'address': '456 Queen St E, Toronto', 'price': 1250000, 'bedrooms': '3', 'bathrooms': '2', 'area': '1500', 'source': 'kijiji'}
    ]

@app.post('/valuate')
def valuate_property(data: dict):
    return {'estimated_value': 830000, 'confidence': 0.845, 'market_analysis': 'Priced competitively'}

@app.post('/video-jobs')
def create_video_job(data: dict):
    return {'id': 'demo-job-123', 'status': 'pending', 'message': 'Demo video job created'}

app.add_middleware(CORSMiddleware, app, allow_origins=['*'])

if __name__ == '__main__':
    print('API running on http://localhost:8000')
    uvicorn.run(app, host='0.0.0.0', port=8000)
