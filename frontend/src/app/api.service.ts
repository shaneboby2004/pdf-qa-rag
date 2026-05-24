import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {

  private base = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  uploadPdf(file: File): Observable<any> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post(`${this.base}/upload`, form);
  }

  pollStatus(collectionName: string): Observable<any> {
    return interval(1000).pipe(
      switchMap(() => this.http.get(`${this.base}/status/${collectionName}`)),
      takeWhile((res: any) => res.status === 'processing', true)
    );
  }

  queryStream(
    question: string,
    collectionName: string,
    onChunk: (text: string) => void,
    onSources: (sources: any[]) => void,
    onDone: () => void,
    onError: () => void
  ): void {
    fetch(`${this.base}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, collection_name: collectionName })
    }).then(async (res) => {
      if (!res.ok) { onError(); return; }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let sourcesReceived = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) { onDone(); break; }

        const text = decoder.decode(value, { stream: true });

        if (!sourcesReceived && text.startsWith('SOURCES:')) {
          const json = text.replace('SOURCES:', '').split('\n')[0];
          try { onSources(JSON.parse(json)); } catch {}
          sourcesReceived = true;
          const rest = text.split('\n').slice(1).join('\n');
          if (rest) onChunk(rest);
        } else {
          onChunk(text);
        }
      }
    }).catch(() => onError());
  }
}