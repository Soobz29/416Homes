import httpx
import time
import sys

def main():
    print("Initiating video job for 120 Clement Road...")
    r = httpx.post('http://localhost:8000/video/create-checkout', json={
        'listing_url': 'https://www.realtor.ca/real-estate/27986877/120-clement-rd-toronto-etobicoke-west-humber-clairville',
        'agent_email': 'james@416homes.com',
        'agent_name': 'James',
        'voice': 'female_luxury'
    })
    
    if r.status_code != 200:
        print("Failed to start job:", r.text)
        sys.exit(1)
        
    job_id = r.json()['job_id']
    print(f'Started job {job_id}')
    
    prev_msg = ''
    while True:
        try:
            res = httpx.get(f'http://localhost:8000/video/status/{job_id}')
            data = res.json()
            msg = f"{data.get('progress_step', '')} - {data.get('progress_message', '')}"
            
            if msg != prev_msg:
                print(msg)
                prev_msg = msg
                
            if data.get('status') in ['completed', 'failed']:
                print('Final status:', data['status'])
                if data.get('error'): 
                    print('Error:', data['error'])
                if data.get('video_path'):
                    print('Video path:', data['video_path'])
                break
        except Exception as e:
            print("Status fetch error:", e)
            
        time.sleep(2)

if __name__ == '__main__':
    main()
