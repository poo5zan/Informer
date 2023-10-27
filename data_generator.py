import pandas as pd

def get_new_data(time_id,id, x1, x2, x3, y):
    return {'time_id':time_id,'stock_id':id,'x1':x1,'x2':x2,'x3':x3, 'y': y}

def generate_data(num_time_ids, num_features, num_of_stocks):
    data = []
    for t in range(1,num_time_ids + 1):
        for s in range(1,num_of_stocks + 1):
            time_id = 't' + str(t)
            stock_id = 's' + str(s)
            row_data = {'time_id': time_id, 'stock_id': stock_id, 'y': 'y' + time_id + stock_id}
            for f in range(1,num_features + 1):
                f_key = 'x'+ str(f)
                row_data[f_key] = time_id + stock_id + f_key

            data.append(row_data)

    return data

data_df = pd.DataFrame(generate_data(10, 3, 4))
print(data_df)

import numpy as np
def create_stock_data(data_df, window_len):
    time_ids = list(data_df['time_id'].unique())
    print('time_ids ', time_ids)
    stock_ids = list(data_df['stock_id'].unique())
    print('stock_ids ', stock_ids)
    features = data_df.columns
    # features = [x for x in data_df.columns if x not in ['time_id', 'stock_id']]
    print('features ', features)
    all_data = []
    time_id_counter = 0
    time_id_batch = []
    for time_id in time_ids:
        time_id_counter += 1
        stock_level_data = []
        for stock_id in stock_ids:            
            row_data = data_df[(data_df['time_id'] == time_id) & (data_df['stock_id'] == stock_id)]
            features_data = row_data[features]
            stock_level_data.append(list(features_data.values[0]))

        time_id_batch.append(stock_level_data)

        if time_id_counter == window_len:
            all_data.append(time_id_batch)
            time_id_batch = []
            time_id_counter = 0
            
    all_data_np = np.array(all_data)
    # print('all_data shape ', all_data_np.shape)
    return all_data_np

# num_records (time_ids), window_length (batch), stocks, features
stock_data_np = create_stock_data(data_df, 2)
print('stock_data_np shape ', stock_data_np.shape)
print(stock_data_np[0])